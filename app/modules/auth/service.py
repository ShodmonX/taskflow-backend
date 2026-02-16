import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password, verify_password
from app.core.config import settings
from app.infra.redis import redis_del, redis_get_json, redis_set_json
from app.modules.auth.tokens import generate_refresh_token, hash_refresh_token
from app.modules.users.models import User
from app.modules.users.repository import UserRepository


def _refresh_ttl_seconds() -> int:
    return int(timedelta(days=settings.refresh_token_days).total_seconds())


def _rt_key(token_hash: str) -> str:
    return f"rt:{token_hash}"


class AuthService:
    """
    AuthService provides authentication-related operations such as user registration, login, and token/session management.

    This service interacts with a user repository and handles the creation and validation of access and refresh tokens,
    as well as session management using Redis for refresh tokens.

    Methods:
        __init__(user_repo: UserRepository | None = None) -> None
            Initializes the AuthService with an optional UserRepository instance.

        async register(db: AsyncSession, email: str, username: str, password: str) -> str
            Raises HTTPException if the email or username is already taken.
            Returns an access token for the newly registered user.

        async login(db: AsyncSession, email: str, password: str) -> User
            Authenticates a user by email and password.
            Raises HTTPException if credentials are invalid or the user is inactive.
            Returns the authenticated User object.

        async create_refresh_session(user_id: str) -> str
            Creates a new refresh session for the specified user.
            Stores the session in Redis and returns the raw refresh token.

        async rotate_refresh_session(raw_refresh_token: str) -> tuple[str, str]
            Raises HTTPException if the provided refresh token is invalid.
            Returns a tuple of the new raw refresh token and the associated user ID.

        async revoke_refresh_session(raw_refresh_token: str) -> None

        async issue_access_token(user_id: str) -> str
            Issues a new access token for the specified user.
    """
    def __init__(self, user_repo: UserRepository | None = None) -> None:
        """
        Initializes the service with a user repository.

        Args:
            user_repo (UserRepository, optional): An instance of UserRepository to be used by the service.
                If not provided, a new UserRepository instance will be created.

        Returns:
            None
        """
        self.user_repo = user_repo or UserRepository()

    async def register(self, db: AsyncSession, email: str, username: str, password: str) -> str:
        """
        Registers a new user with the provided email, username, and password.

        Args:
            db (AsyncSession): The asynchronous database session.
            email (str): The email address of the new user.
            username (str): The username for the new user.
            password (str): The plaintext password for the new user.

        Raises:
            HTTPException: If the email is already registered (status code 409).
            HTTPException: If the username is already taken (status code 409).

        Returns:
            str: An access token for the newly registered user.
        """
        if await self.user_repo.get_by_email(db, email):
            raise HTTPException(status_code=409, detail="Email already registered")
        if await self.user_repo.get_by_username(db, username):
            raise HTTPException(status_code=409, detail="Username already taken")

        user = User(email=email, username=username, hashed_password=hash_password(password))
        await self.user_repo.create(db, user)
        await db.commit()

        return create_access_token(subject=str(user.id))

    async def login(self, db: AsyncSession, email: str, password: str) -> User:
        """
        Authenticate a user by email and password.

        Args:
            db (AsyncSession): The database session to use for querying the user.
            email (str): The email address of the user attempting to log in.
            password (str): The plaintext password provided by the user.

        Returns:
            User: The authenticated user object if credentials are valid and the user is active.

        Raises:
            HTTPException: If the credentials are invalid (401 Unauthorized) or the user is inactive (403 Forbidden).
        """
        user = await self.user_repo.get_by_email(db, email)
        if not user or not verify_password(password, user.hashed_password):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is inactive")
        return user

    async def create_refresh_session(self, user_id: str) -> str:
        """
        Asynchronously creates a new refresh session for the specified user.

        Generates a new refresh token, hashes it, and associates it with a unique session ID.
        Stores the session payload in Redis with a time-to-live (TTL) value.

        Args:
            user_id (str): The unique identifier of the user for whom the refresh session is created.

        Returns:
            str: The raw (unhashed) refresh token to be provided to the client.
        """
        raw = generate_refresh_token()
        h = hash_refresh_token(raw)
        sid = str(uuid.uuid4())

        payload = {
            "sid": sid,
            "uid": user_id,
            "created_at": int(datetime.now(timezone.utc).timestamp()),
        }
        await redis_set_json(_rt_key(h), payload, ttl_seconds=_refresh_ttl_seconds())
        return raw

    async def rotate_refresh_session(self, raw_refresh_token: str) -> tuple[str, str]:
        """
        Rotates a refresh session by invalidating the old refresh token and issuing a new one.

        Args:
            raw_refresh_token (str): The raw refresh token provided by the client.

        Returns:
            tuple[str, str]: A tuple containing the new raw refresh token and the associated user ID.

        Raises:
            HTTPException: If the provided refresh token is invalid or the session does not exist.

        Side Effects:
            - Deletes the old refresh session from Redis.
            - Creates a new refresh session in Redis with a new session ID and updated metadata.
        """
        old_hash = hash_refresh_token(raw_refresh_token)
        old_key = _rt_key(old_hash)

        session = await redis_get_json(old_key)
        if not session:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

        user_id = session["uid"]

        # revoke old
        await redis_del(old_key)

        # issue new
        new_raw = generate_refresh_token()
        new_hash = hash_refresh_token(new_raw)
        new_key = _rt_key(new_hash)

        new_payload = {
            "sid": str(uuid.uuid4()),
            "uid": user_id,
            "created_at": int(datetime.now(timezone.utc).timestamp()),
            "rotated_from": session.get("sid"),
        }
        await redis_set_json(new_key, new_payload, ttl_seconds=_refresh_ttl_seconds())

        return new_raw, user_id

    async def revoke_refresh_session(self, raw_refresh_token: str) -> None:
        """
        Revokes a refresh session by deleting the corresponding refresh token from Redis.

        Args:
            raw_refresh_token (str): The raw refresh token to be revoked.

        Returns:
            None

        Raises:
            Any exceptions raised by the underlying Redis deletion operation.
        """
        h = hash_refresh_token(raw_refresh_token)
        await redis_del(_rt_key(h))

    async def issue_access_token(self, user_id: str) -> str:
        """
        Asynchronously issues a new access token for the specified user.

        Args:
            user_id (str): The unique identifier of the user for whom the access token is to be issued.

        Returns:
            str: A newly generated access token for the user.
        """
        return create_access_token(subject=user_id)
