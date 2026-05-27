"""create messages

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-24
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("business_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sender_type", sa.String(length=50), nullable=False),
        sa.Column("direction", sa.String(length=50), nullable=False),
        sa.Column("channel", sa.String(length=50), nullable=False),
        sa.Column("message_text", sa.Text(), nullable=False),
        sa.Column("message_type", sa.String(length=50), nullable=False, server_default="text"),
        sa.Column("external_message_id", sa.String(length=255), nullable=True),
        sa.Column("raw_payload", postgresql.JSONB(), nullable=True),
        sa.Column("ai_metadata", postgresql.JSONB(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"]),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("messages_tenant_id_idx", "messages", ["tenant_id"])
    op.create_index("messages_business_id_idx", "messages", ["business_id"])
    op.create_index("messages_conversation_id_idx", "messages", ["conversation_id"])
    op.create_index("messages_created_at_idx", "messages", ["created_at"])
    op.create_index("messages_external_message_id_idx", "messages", ["external_message_id"])


def downgrade() -> None:
    op.drop_index("messages_external_message_id_idx", table_name="messages")
    op.drop_index("messages_created_at_idx", table_name="messages")
    op.drop_index("messages_conversation_id_idx", table_name="messages")
    op.drop_index("messages_business_id_idx", table_name="messages")
    op.drop_index("messages_tenant_id_idx", table_name="messages")
    op.drop_table("messages")
