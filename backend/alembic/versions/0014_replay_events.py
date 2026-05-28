"""replay_events — E3.1c retry/replay observability

Revision ID: 0014
Revises: 0013
Create Date: 2026-05-28
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "replay_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("business_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("flow_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("trace_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("delivery_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("inbound_message_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("outbound_message_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("idempotency_key", sa.Text(), nullable=True),
        sa.Column("external_message_id", sa.Text(), nullable=True),
        sa.Column("correlation_id", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=False), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"]),
    )
    op.create_index(
        "replay_events_business_conversation_created_idx",
        "replay_events",
        ["business_id", "conversation_id", "created_at"],
    )
    op.create_index(
        "replay_events_business_idempotency_created_idx",
        "replay_events",
        ["business_id", "idempotency_key", "created_at"],
    )
    op.create_index("replay_events_trace_id_idx", "replay_events", ["trace_id"])
    op.create_index("replay_events_delivery_id_idx", "replay_events", ["delivery_id"])
    op.create_index(
        "replay_events_event_type_created_idx",
        "replay_events",
        ["event_type", "created_at"],
    )
    op.create_index("replay_events_tenant_id_idx", "replay_events", ["tenant_id"])
    op.create_index("replay_events_business_id_idx", "replay_events", ["business_id"])


def downgrade() -> None:
    op.drop_index("replay_events_business_id_idx", table_name="replay_events")
    op.drop_index("replay_events_tenant_id_idx", table_name="replay_events")
    op.drop_index("replay_events_event_type_created_idx", table_name="replay_events")
    op.drop_index("replay_events_delivery_id_idx", table_name="replay_events")
    op.drop_index("replay_events_trace_id_idx", table_name="replay_events")
    op.drop_index(
        "replay_events_business_idempotency_created_idx",
        table_name="replay_events",
    )
    op.drop_index(
        "replay_events_business_conversation_created_idx",
        table_name="replay_events",
    )
    op.drop_table("replay_events")
