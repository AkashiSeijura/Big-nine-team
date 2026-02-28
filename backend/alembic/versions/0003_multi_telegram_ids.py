"""multi telegram ids per user

Revision ID: 0003
Revises: 0002
Create Date: 2026-02-28
"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_telegram_ids",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("telegram_id"),
    )
    op.create_index("ix_user_telegram_ids_user_id", "user_telegram_ids", ["user_id"])

    # Перенести существующие данные
    op.execute(
        """
        INSERT INTO user_telegram_ids (user_id, telegram_id)
        SELECT id, telegram_id FROM users WHERE telegram_id IS NOT NULL
        """
    )

    op.drop_index("ix_users_telegram_id", table_name="users")
    op.drop_column("users", "telegram_id")


def downgrade() -> None:
    op.add_column("users", sa.Column("telegram_id", sa.BigInteger(), nullable=True))
    op.execute(
        """
        UPDATE users
        SET telegram_id = (
            SELECT telegram_id FROM user_telegram_ids
            WHERE user_id = users.id
            LIMIT 1
        )
        """
    )
    op.create_index("ix_users_telegram_id", "users", ["telegram_id"], unique=True)
    op.drop_index("ix_user_telegram_ids_user_id", table_name="user_telegram_ids")
    op.drop_table("user_telegram_ids")
