"""retry_attempts — E3.2a operational retry lifecycle audit

Revision ID: 0015
Revises: 0014
Create Date: 2026-05-28
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0015"
down_revision: str | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "retry_attempts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("business_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scope_type", sa.Text(), nullable=False),
        sa.Column("scope_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("trace_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("error_type", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("correlation_id", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=False), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"]),
    )
    op.create_index(
        "retry_attempts_scope_idx",
        "retry_attempts",
        ["business_id", "scope_type", "scope_id", "created_at"],
    )
    op.create_index(
        "retry_attempts_conversation_idx",
        "retry_attempts",
        ["business_id", "conversation_id", "created_at"],
    )
    op.create_index("retry_attempts_trace_id_idx", "retry_attempts", ["trace_id"])
    op.create_index("retry_attempts_tenant_id_idx", "retry_attempts", ["tenant_id"])
    op.create_index("retry_attempts_business_id_idx", "retry_attempts", ["business_id"])


def downgrade() -> None:
    op.drop_index("retry_attempts_business_id_idx", table_name="retry_attempts")
    op.drop_index("retry_attempts_tenant_id_idx", table_name="retry_attempts")
    op.drop_index("retry_attempts_trace_id_idx", table_name="retry_attempts")
    op.drop_index("retry_attempts_conversation_idx", table_name="retry_attempts")
    op.drop_index("retry_attempts_scope_idx", table_name="retry_attempts")
    op.drop_table("retry_attempts")
