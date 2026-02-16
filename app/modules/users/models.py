import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, func, Index, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class User(Base):
    """
    Represents a user in the system.

    Attributes:
        id (uuid.UUID): Unique identifier for the user.
        email (str): User's email address. Must be unique.
        username (str): User's username. Must be unique.
        hashed_password (str): Hashed password for authentication.
        is_active (bool): Indicates if the user account is active. Defaults to True.
        is_verified (bool): Indicates if the user's email is verified. Defaults to False.
        is_superuser (bool): Indicates if the user has superuser privileges. Defaults to False.
        created_at (datetime): Timestamp when the user was created.
        updated_at (datetime): Timestamp when the user was last updated.

    Table Constraints:
        - Unique constraint on email.
        - Unique constraint on username.
        - Index on email.
        - Index on username.
    """
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("email", name="uq_users_email"),
        UniqueConstraint("username", name="uq_users_username"),
        Index("ix_users_email", "email"),
        Index("ix_users_username", "username"),
    )

    id:                 Mapped[uuid.UUID] =     mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    email:              Mapped[str] =           mapped_column(String(255), nullable=False)
    username:           Mapped[str] =           mapped_column(String(50), nullable=False)
    hashed_password:    Mapped[str] =           mapped_column(String(255), nullable=False)

    is_active:          Mapped[bool] =          mapped_column(Boolean, nullable=False, server_default=text("'true'::boolean"))
    is_verified:        Mapped[bool] =          mapped_column(Boolean, nullable=False, server_default=text("'false'::boolean"))
    is_superuser:       Mapped[bool] =          mapped_column(Boolean, nullable=False, server_default=text("'false'::boolean"))

    created_at:         Mapped[datetime] =      mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at:         Mapped[datetime] =      mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
