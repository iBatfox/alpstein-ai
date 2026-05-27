"""create customers

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-24
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "customers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("business_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("language", sa.String(length=20), nullable=True),
        sa.Column("external_customer_id", sa.String(length=255), nullable=True),
        sa.Column("source_channel", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("business_id", "phone"),
        sa.UniqueConstraint("business_id", "source_channel", "external_customer_id"),
    )
    op.create_index("customers_tenant_id_idx", "customers", ["tenant_id"])
    op.create_index("customers_business_id_idx", "customers", ["business_id"])
    op.create_index("customers_phone_idx", "customers", ["phone"])
    op.create_index(
        "customers_business_channel_external_id_idx",
        "customers",
        ["business_id", "source_channel", "external_customer_id"],
    )


def downgrade() -> None:
    op.drop_index("customers_business_channel_external_id_idx", table_name="customers")
    op.drop_index("customers_phone_idx", table_name="customers")
    op.drop_index("customers_business_id_idx", table_name="customers")
    op.drop_index("customers_tenant_id_idx", table_name="customers")
    op.drop_table("customers")
