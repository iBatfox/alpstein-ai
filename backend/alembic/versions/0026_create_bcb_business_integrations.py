"""create_bcb_business_integrations

Revision ID: 0026
Revises: 0025
Create Date: 2026-06-08
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0026"
down_revision: str | None = "0025"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "business_context_builder"
ALLOWED_USERS_TABLE = "mini_app_allowed_users"
INTEGRATIONS_TABLE = "business_integrations"


def upgrade() -> None:
    op.add_column(
        ALLOWED_USERS_TABLE,
        sa.Column("alpstein_business_id", sa.Text(), nullable=True),
        schema=SCHEMA,
    )
    op.create_index(
        "bcb_mini_app_allowed_users_business_id_idx",
        ALLOWED_USERS_TABLE,
        ["alpstein_business_id"],
        schema=SCHEMA,
    )

    op.create_table(
        INTEGRATIONS_TABLE,
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("alpstein_business_id", sa.Text(), nullable=False),
        sa.Column("channel_type", sa.Text(), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("external_channel_id", sa.Text(), nullable=True),
        sa.Column("provider", sa.Text(), nullable=True),
        sa.Column("workflow_name", sa.Text(), nullable=True),
        sa.Column("workflow_id", sa.Text(), nullable=True),
        sa.Column("backend_route", sa.Text(), nullable=True),
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
        schema=SCHEMA,
    )
    op.create_index(
        "bcb_business_integrations_business_id_idx",
        INTEGRATIONS_TABLE,
        ["alpstein_business_id"],
        schema=SCHEMA,
    )
    op.create_index(
        "bcb_business_integrations_business_status_idx",
        INTEGRATIONS_TABLE,
        ["alpstein_business_id", "status"],
        schema=SCHEMA,
    )
    op.create_index(
        "bcb_business_integrations_channel_type_idx",
        INTEGRATIONS_TABLE,
        ["channel_type"],
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_index(
        "bcb_business_integrations_channel_type_idx",
        table_name=INTEGRATIONS_TABLE,
        schema=SCHEMA,
    )
    op.drop_index(
        "bcb_business_integrations_business_status_idx",
        table_name=INTEGRATIONS_TABLE,
        schema=SCHEMA,
    )
    op.drop_index(
        "bcb_business_integrations_business_id_idx",
        table_name=INTEGRATIONS_TABLE,
        schema=SCHEMA,
    )
    op.drop_table(INTEGRATIONS_TABLE, schema=SCHEMA)

    op.drop_index(
        "bcb_mini_app_allowed_users_business_id_idx",
        table_name=ALLOWED_USERS_TABLE,
        schema=SCHEMA,
    )
    op.drop_column(ALLOWED_USERS_TABLE, "alpstein_business_id", schema=SCHEMA)
