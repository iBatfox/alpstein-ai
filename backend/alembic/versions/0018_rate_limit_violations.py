"""rate_limit_violations — E3.5c ingress rate limit audit

Revision ID: 0018
Revises: 0017
Create Date: 2026-05-28
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0018"
down_revision: str | None = "0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "rate_limit_violations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("business_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scope_type", sa.String(length=50), nullable=False),
        sa.Column("scope_key", sa.String(length=255), nullable=False),
        sa.Column("channel", sa.String(length=50), nullable=True),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("limit_value", sa.Integer(), nullable=False),
        sa.Column("window_seconds", sa.Integer(), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=False), nullable=False),
        sa.Column("observed_count", sa.Integer(), nullable=False),
        sa.Column("correlation_id", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=False), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"]),
    )
    op.create_index(
        "rate_limit_violations_business_created_idx",
        "rate_limit_violations",
        ["business_id", "created_at"],
    )
    op.create_index(
        "rate_limit_violations_business_channel_created_idx",
        "rate_limit_violations",
        ["business_id", "channel", "created_at"],
    )
    op.create_index(
        "rate_limit_violations_scope_created_idx",
        "rate_limit_violations",
        ["scope_type", "created_at"],
    )
    op.create_index(
        "rate_limit_violations_tenant_id_idx",
        "rate_limit_violations",
        ["tenant_id"],
    )
    op.create_index(
        "rate_limit_violations_business_id_idx",
        "rate_limit_violations",
        ["business_id"],
    )
    op.create_index(
        "rate_limit_violations_conversation_id_idx",
        "rate_limit_violations",
        ["conversation_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "rate_limit_violations_conversation_id_idx",
        table_name="rate_limit_violations",
    )
    op.drop_index(
        "rate_limit_violations_business_id_idx",
        table_name="rate_limit_violations",
    )
    op.drop_index(
        "rate_limit_violations_tenant_id_idx",
        table_name="rate_limit_violations",
    )
    op.drop_index(
        "rate_limit_violations_scope_created_idx",
        table_name="rate_limit_violations",
    )
    op.drop_index(
        "rate_limit_violations_business_channel_created_idx",
        table_name="rate_limit_violations",
    )
    op.drop_index(
        "rate_limit_violations_business_created_idx",
        table_name="rate_limit_violations",
    )
    op.drop_table("rate_limit_violations")
