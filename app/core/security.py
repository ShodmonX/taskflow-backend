from datetime import datetime, timedelta, timezone

from jose import jwt
from passlib.context import CryptContext

from app.core.config import settings


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """
    Hashes a plain-text password using the configured password context.

    Args:
        password (str): The plain-text password to be hashed.

    Returns:
        str: The hashed password.
    """
    return pwd_context.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    """
    Verifies that the provided plain-text password matches the given hashed password.

    Args:
        password (str): The plain-text password to verify.
        hashed_password (str): The hashed password to compare against.

    Returns:
        bool: True if the password matches the hash, False otherwise.
    """
    return pwd_context.verify(password, hashed_password)


def create_access_token(subject: str) -> str:
    """
    Generates a JSON Web Token (JWT) access token for the given subject.

    Args:
        subject (str): The subject (typically user identifier) to include in the token payload.

    Returns:
        str: The encoded JWT access token as a string.

    Raises:
        Any exceptions raised by the underlying JWT library.

    Notes:
        - The token will expire after a duration specified by `settings.access_token_expire_minutes`.
        - The token is signed using the secret and algorithm specified in `settings.jwt_secret` and `settings.jwt_alg`.
    """
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_alg)


def decode_token(token: str) -> dict:
    """
    Decodes a JWT token using the application's secret and algorithm.

    Args:
        token (str): The JWT token to decode.

    Returns:
        dict: The decoded payload of the JWT token.

    Raises:
        jwt.ExpiredSignatureError: If the token has expired.
        jwt.InvalidTokenError: If the token is invalid or cannot be decoded.
    """
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_alg])
