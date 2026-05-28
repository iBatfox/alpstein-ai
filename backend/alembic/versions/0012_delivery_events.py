"""delivery_events table — E2.6 outbound delivery visibility

Revision ID: 0012
Revises: 0011
Create Date: 2026-05-28
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "delivery_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("business_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("flow_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("trace_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("outbound_message_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("channel", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("provider_message_id", sa.String(length=255), nullable=True),
        sa.Column("provider_status", sa.String(length=100), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_type", sa.String(length=100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
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
        sa.Column("delivered_at", sa.DateTime(timezone=False), nullable=True),
        sa.Column("failed_at", sa.DateTime(timezone=False), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"]),
        sa.ForeignKeyConstraint(["flow_id"], ["flows.id"]),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"]),
        sa.ForeignKeyConstraint(["trace_id"], ["message_traces.id"]),
        sa.ForeignKeyConstraint(["outbound_message_id"], ["messages.id"]),
    )
    op.create_index(
        "delivery_events_outbound_message_id_unique",
        "delivery_events",
        ["outbound_message_id"],
        unique=True,
    )
    op.create_index("delivery_events_trace_id_idx", "delivery_events", ["trace_id"])
    op.create_index("delivery_events_tenant_id_idx", "delivery_events", ["tenant_id"])
    op.create_index(
        "delivery_events_business_id_idx", "delivery_events", ["business_id"]
    )
    op.create_index(
        "delivery_events_conversation_id_idx",
        "delivery_events",
        ["conversation_id"],
    )
    op.create_index(
        "delivery_events_business_channel_status_idx",
        "delivery_events",
        ["business_id", "channel", "status"],
    )
    op.create_index(
        "delivery_events_created_at_idx",
        "delivery_events",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index("delivery_events_created_at_idx", table_name="delivery_events")
    op.drop_index(
        "delivery_events_business_channel_status_idx",
        table_name="delivery_events",
    )
    op.drop_index("delivery_events_conversation_id_idx", table_name="delivery_events")
    op.drop_index("delivery_events_business_id_idx", table_name="delivery_events")
    op.drop_index("delivery_events_tenant_id_idx", table_name="delivery_events")
    op.drop_index("delivery_events_trace_id_idx", table_name="delivery_events")
    op.drop_index(
        "delivery_events_outbound_message_id_unique",
        table_name="delivery_events",
    )
    op.drop_table("delivery_events")
