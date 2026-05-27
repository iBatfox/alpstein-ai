"""create tenants and businesses

Revision ID: 0001
Revises:
Create Date: 2026-05-24
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("tenants_slug_idx", "tenants", ["slug"])
    op.create_index("tenants_status_idx", "tenants", ["status"])

    op.create_table(
        "businesses",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("business_type", sa.String(length=100), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("website", sa.String(length=255), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("working_hours", postgresql.JSONB(), nullable=True),
        sa.Column("language", sa.String(length=20), nullable=True, server_default="de"),
        sa.Column("timezone", sa.String(length=100), nullable=True, server_default="Europe/Zurich"),
        sa.Column("ai_prompt", sa.Text(), nullable=True),
        sa.Column("ai_tone", sa.String(length=100), nullable=True),
        sa.Column("ai_language", sa.String(length=20), nullable=True),
        sa.Column("storage_mode", sa.String(length=50), nullable=False, server_default="shared"),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("external_id"),
    )
    op.create_index("businesses_tenant_id_idx", "businesses", ["tenant_id"])
    op.create_index("businesses_external_id_idx", "businesses", ["external_id"])
    op.create_index("businesses_status_idx", "businesses", ["status"])


def downgrade() -> None:
    op.drop_index("businesses_status_idx", table_name="businesses")
    op.drop_index("businesses_external_id_idx", table_name="businesses")
    op.drop_index("businesses_tenant_id_idx", table_name="businesses")
    op.drop_table("businesses")

    op.drop_index("tenants_status_idx", table_name="tenants")
    op.drop_index("tenants_slug_idx", table_name="tenants")
    op.drop_table("tenants")
