"""inbound_processing_locks — E3.1a single-owner processing per idempotency scope

Revision ID: 0013
Revises: 0012
Create Date: 2026-05-28
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "inbound_processing_locks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("business_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("flow_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("channel", sa.String(length=50), nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("external_message_id", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("owner_correlation_id", sa.String(length=255), nullable=False),
        sa.Column("replay_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("first_seen_at", sa.DateTime(timezone=False), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=False), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=False), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"]),
        sa.ForeignKeyConstraint(["flow_id"], ["flows.id"]),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"]),
    )
    op.create_index(
        "inbound_processing_locks_scope_unique",
        "inbound_processing_locks",
        ["business_id", "conversation_id", "idempotency_key"],
        unique=True,
    )
    op.create_index(
        "inbound_processing_locks_tenant_id_idx",
        "inbound_processing_locks",
        ["tenant_id"],
    )
    op.create_index(
        "inbound_processing_locks_business_id_idx",
        "inbound_processing_locks",
        ["business_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "inbound_processing_locks_business_id_idx",
        table_name="inbound_processing_locks",
    )
    op.drop_index(
        "inbound_processing_locks_tenant_id_idx",
        table_name="inbound_processing_locks",
    )
    op.drop_index(
        "inbound_processing_locks_scope_unique",
        table_name="inbound_processing_locks",
    )
    op.drop_table("inbound_processing_locks")
