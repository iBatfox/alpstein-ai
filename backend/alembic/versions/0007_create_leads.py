"""create leads

Revision ID: 0007
Revises: 0006
Create Date: 2026-05-24
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "leads",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("business_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("service_requested", sa.String(length=255), nullable=True),
        sa.Column("preferred_date", sa.Date(), nullable=True),
        sa.Column("preferred_time", sa.Time(), nullable=True),
        sa.Column("customer_note", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="new"),
        sa.Column("priority", sa.String(length=50), nullable=True, server_default="normal"),
        sa.Column("source_channel", sa.String(length=50), nullable=True),
        sa.Column("ai_summary", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"]),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"]),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("leads_tenant_id_idx", "leads", ["tenant_id"])
    op.create_index("leads_business_id_idx", "leads", ["business_id"])
    op.create_index("leads_customer_id_idx", "leads", ["customer_id"])
    op.create_index("leads_status_idx", "leads", ["status"])
    op.create_index("leads_created_at_idx", "leads", ["created_at"])


def downgrade() -> None:
    op.drop_index("leads_created_at_idx", table_name="leads")
    op.drop_index("leads_status_idx", table_name="leads")
    op.drop_index("leads_customer_id_idx", table_name="leads")
    op.drop_index("leads_business_id_idx", table_name="leads")
    op.drop_index("leads_tenant_id_idx", table_name="leads")
    op.drop_table("leads")
