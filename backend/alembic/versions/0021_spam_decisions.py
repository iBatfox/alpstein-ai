"""spam_decisions — E3.6c spam protection audit stream

Revision ID: 0021
Revises: 0020
Create Date: 2026-05-28
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0021"
down_revision: str | None = "0020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "spam_decisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("business_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rule_id", sa.String(length=64), nullable=False),
        sa.Column("scope_type", sa.String(length=32), nullable=False),
        sa.Column("scope_key", sa.String(length=255), nullable=False),
        sa.Column("channel", sa.String(length=50), nullable=True),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("decision", sa.String(length=32), nullable=False),
        sa.Column("outcome", sa.String(length=32), nullable=False),
        sa.Column("observed_count", sa.Integer(), nullable=True),
        sa.Column("threshold", sa.Integer(), nullable=True),
        sa.Column("window_seconds", sa.Integer(), nullable=True),
        sa.Column("containment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("correlation_id", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=False), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"]),
        sa.ForeignKeyConstraint(["containment_id"], ["spam_containments.id"]),
    )
    op.create_index(
        "spam_decisions_business_created_idx",
        "spam_decisions",
        ["business_id", "created_at"],
    )
    op.create_index(
        "spam_decisions_business_channel_created_idx",
        "spam_decisions",
        ["business_id", "channel", "created_at"],
    )
    op.create_index(
        "spam_decisions_rule_created_idx",
        "spam_decisions",
        ["rule_id", "created_at"],
    )
    op.create_index("spam_decisions_tenant_id_idx", "spam_decisions", ["tenant_id"])
    op.create_index("spam_decisions_business_id_idx", "spam_decisions", ["business_id"])
    op.create_index(
        "spam_decisions_conversation_id_idx",
        "spam_decisions",
        ["conversation_id"],
    )


def downgrade() -> None:
    op.drop_index("spam_decisions_conversation_id_idx", table_name="spam_decisions")
    op.drop_index("spam_decisions_business_id_idx", table_name="spam_decisions")
    op.drop_index("spam_decisions_tenant_id_idx", table_name="spam_decisions")
    op.drop_index("spam_decisions_rule_created_idx", table_name="spam_decisions")
    op.drop_index(
        "spam_decisions_business_channel_created_idx",
        table_name="spam_decisions",
    )
    op.drop_index("spam_decisions_business_created_idx", table_name="spam_decisions")
    op.drop_table("spam_decisions")
