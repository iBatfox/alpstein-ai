"""create conversations

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-24
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "conversations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("business_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("channel", sa.String(length=50), nullable=False),
        sa.Column("external_conversation_id", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="open"),
        sa.Column("is_ai_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("last_message_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"]),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("conversations_tenant_id_idx", "conversations", ["tenant_id"])
    op.create_index("conversations_business_id_idx", "conversations", ["business_id"])
    op.create_index("conversations_customer_id_idx", "conversations", ["customer_id"])
    op.create_index("conversations_status_idx", "conversations", ["status"])


def downgrade() -> None:
    op.drop_index("conversations_status_idx", table_name="conversations")
    op.drop_index("conversations_customer_id_idx", table_name="conversations")
    op.drop_index("conversations_business_id_idx", table_name="conversations")
    op.drop_index("conversations_tenant_id_idx", table_name="conversations")
    op.drop_table("conversations")
