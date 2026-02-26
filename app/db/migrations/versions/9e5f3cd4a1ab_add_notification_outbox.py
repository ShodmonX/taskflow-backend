"""add notification outbox

Revision ID: 9e5f3cd4a1ab
Revises: 7a893edc6a5b
Create Date: 2026-02-26 14:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9e5f3cd4a1ab"
down_revision: Union[str, Sequence[str], None] = "7a893edc6a5b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "notification_outbox",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_notification_outbox_status_next_retry",
        "notification_outbox",
        ["status", "next_retry_at"],
        unique=False,
    )
    op.create_index(
        "ix_notification_outbox_created_at",
        "notification_outbox",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_notification_outbox_created_at", table_name="notification_outbox")
    op.drop_index("ix_notification_outbox_status_next_retry", table_name="notification_outbox")
    op.drop_table("notification_outbox")
