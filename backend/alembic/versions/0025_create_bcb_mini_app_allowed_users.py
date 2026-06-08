"""create_bcb_mini_app_allowed_users

Revision ID: 0025
Revises: 0024
Create Date: 2026-06-08
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0025"
down_revision: str | None = "0024"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "business_context_builder"
TABLE = "mini_app_allowed_users"


def upgrade() -> None:
    op.create_table(
        TABLE,
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("telegram_user_id", sa.BigInteger(), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("company_name", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=50),
            nullable=False,
            server_default="active",
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=False),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=False),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "status IN ('active', 'disabled')",
            name="business_context_builder_mini_app_allowed_users_status_check",
        ),
        sa.UniqueConstraint(
            "telegram_user_id",
            name="business_context_builder_mini_app_allowed_users_telegram_user_id_unique",
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "bcb_mini_app_allowed_users_telegram_user_id_idx",
        TABLE,
        ["telegram_user_id"],
        schema=SCHEMA,
    )
    op.create_index(
        "bcb_mini_app_allowed_users_status_idx",
        TABLE,
        ["status"],
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_index(
        "bcb_mini_app_allowed_users_status_idx",
        table_name=TABLE,
        schema=SCHEMA,
    )
    op.drop_index(
        "bcb_mini_app_allowed_users_telegram_user_id_idx",
        table_name=TABLE,
        schema=SCHEMA,
    )
    op.drop_table(TABLE, schema=SCHEMA)
