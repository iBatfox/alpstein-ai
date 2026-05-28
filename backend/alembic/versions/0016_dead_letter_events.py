"""dead_letter_events — E3.2b permanently failed operations

Revision ID: 0016
Revises: 0015
Create Date: 2026-05-28
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0016"
down_revision: str | None = "0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "dead_letter_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("business_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("flow_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("trace_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("delivery_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("inbound_message_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("outbound_message_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("scope_type", sa.Text(), nullable=False),
        sa.Column("scope_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("failure_reason", sa.Text(), nullable=False),
        sa.Column("error_type", sa.Text(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("correlation_id", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=False), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=False), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=False), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"]),
    )
    op.create_index(
        "dead_letter_events_active_scope_unique",
        "dead_letter_events",
        ["business_id", "scope_type", "scope_id"],
        unique=True,
        postgresql_where=sa.text("resolved_at IS NULL"),
    )
    op.create_index(
        "dead_letter_events_business_conversation_idx",
        "dead_letter_events",
        ["business_id", "conversation_id", "created_at"],
    )
    op.create_index("dead_letter_events_delivery_id_idx", "dead_letter_events", ["delivery_id"])
    op.create_index("dead_letter_events_trace_id_idx", "dead_letter_events", ["trace_id"])
    op.create_index("dead_letter_events_tenant_id_idx", "dead_letter_events", ["tenant_id"])
    op.create_index("dead_letter_events_business_id_idx", "dead_letter_events", ["business_id"])


def downgrade() -> None:
    op.drop_index("dead_letter_events_business_id_idx", table_name="dead_letter_events")
    op.drop_index("dead_letter_events_tenant_id_idx", table_name="dead_letter_events")
    op.drop_index("dead_letter_events_trace_id_idx", table_name="dead_letter_events")
    op.drop_index("dead_letter_events_delivery_id_idx", table_name="dead_letter_events")
    op.drop_index(
        "dead_letter_events_business_conversation_idx",
        table_name="dead_letter_events",
    )
    op.drop_index(
        "dead_letter_events_active_scope_unique",
        table_name="dead_letter_events",
    )
    op.drop_table("dead_letter_events")
