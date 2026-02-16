from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users.models import User


class UserRepository:
    """
    Repository for managing User entities in the database.
    """
    async def get_by_email(self, db: AsyncSession, email: str) -> User | None:
        """
        Retrieve a user from the database by their email address.
        Args:
            db (AsyncSession): The asynchronous database session to use for the query.
            email (str): The email address of the user to retrieve.
        Returns:
            User | None: The user instance if found, otherwise None.
        """
        res = await db.execute(select(User).where(User.email == email))
        return res.scalar_one_or_none()

    async def get_by_username(self, db: AsyncSession, username: str) -> User | None:
        """
        Retrieve a user by their username.

        Args:
            db (AsyncSession): The asynchronous database session.
            username (str): The username of the user to retrieve.

        Returns:
            User | None: The user instance if found, otherwise None.
        """
        res = await db.execute(select(User).where(User.username == username))
        return res.scalar_one_or_none()

    async def create(self, db: AsyncSession, user: User) -> User:
        """
        Asynchronously adds a new User instance to the database session and flushes the session.
        Args:
            db (AsyncSession): The asynchronous database session to use for adding the user.
            user (User): The User instance to be added to the database.
        Returns:
            User: The User instance that was added to the session.
        """
        db.add(user)
        await db.flush()
        return user
