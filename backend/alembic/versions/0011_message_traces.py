"""message_traces table — E2.4 inbound processing lifecycle

Revision ID: 0011
Revises: 0010
Create Date: 2026-05-28
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "message_traces",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("business_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("flow_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("inbound_message_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("outbound_message_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("channel", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("external_trace_id", sa.String(length=255), nullable=True),
        sa.Column("langfuse_trace_id", sa.String(length=255), nullable=True),
        sa.Column("flow_key", sa.String(length=100), nullable=True),
        sa.Column("external_conversation_id", sa.String(length=255), nullable=True),
        sa.Column("external_message_id", sa.String(length=255), nullable=True),
        sa.Column("idempotency_key", sa.String(length=255), nullable=True),
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
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"]),
        sa.ForeignKeyConstraint(["flow_id"], ["flows.id"]),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"]),
        sa.ForeignKeyConstraint(["inbound_message_id"], ["messages.id"]),
        sa.ForeignKeyConstraint(["outbound_message_id"], ["messages.id"]),
    )
    op.create_index(
        "message_traces_inbound_message_id_unique",
        "message_traces",
        ["inbound_message_id"],
        unique=True,
    )
    op.create_index("message_traces_tenant_id_idx", "message_traces", ["tenant_id"])
    op.create_index("message_traces_business_id_idx", "message_traces", ["business_id"])
    op.create_index("message_traces_flow_id_idx", "message_traces", ["flow_id"])
    op.create_index(
        "message_traces_conversation_id_idx",
        "message_traces",
        ["conversation_id"],
    )
    op.create_index("message_traces_status_idx", "message_traces", ["status"])
    op.create_index(
        "message_traces_flow_id_created_at_idx",
        "message_traces",
        ["flow_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("message_traces_flow_id_created_at_idx", table_name="message_traces")
    op.drop_index("message_traces_status_idx", table_name="message_traces")
    op.drop_index("message_traces_conversation_id_idx", table_name="message_traces")
    op.drop_index("message_traces_flow_id_idx", table_name="message_traces")
    op.drop_index("message_traces_business_id_idx", table_name="message_traces")
    op.drop_index("message_traces_tenant_id_idx", table_name="message_traces")
    op.drop_index(
        "message_traces_inbound_message_id_unique",
        table_name="message_traces",
    )
    op.drop_table("message_traces")
