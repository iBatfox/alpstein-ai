"""spam_indicator_buckets — E3.6a spam signal counters

Revision ID: 0019
Revises: 0018
Create Date: 2026-05-28
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0019"
down_revision: str | None = "0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "spam_indicator_buckets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("business_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rule_id", sa.String(length=64), nullable=False),
        sa.Column("scope_type", sa.String(length=32), nullable=False),
        sa.Column("scope_key", sa.String(length=255), nullable=False),
        sa.Column("channel", sa.String(length=50), nullable=True),
        sa.Column("window_start", sa.DateTime(timezone=False), nullable=False),
        sa.Column("window_seconds", sa.Integer(), nullable=False),
        sa.Column("signal_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=False), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=False), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"]),
    )
    op.create_index(
        "spam_indicator_buckets_unique",
        "spam_indicator_buckets",
        ["tenant_id", "business_id", "rule_id", "scope_type", "scope_key", "window_start"],
        unique=True,
    )
    op.create_index(
        "spam_indicator_buckets_business_rule_window_idx",
        "spam_indicator_buckets",
        ["business_id", "rule_id", "window_start"],
    )
    op.create_index(
        "spam_indicator_buckets_tenant_id_idx",
        "spam_indicator_buckets",
        ["tenant_id"],
    )
    op.create_index(
        "spam_indicator_buckets_business_id_idx",
        "spam_indicator_buckets",
        ["business_id"],
    )


def downgrade() -> None:
    op.drop_index("spam_indicator_buckets_business_id_idx", table_name="spam_indicator_buckets")
    op.drop_index("spam_indicator_buckets_tenant_id_idx", table_name="spam_indicator_buckets")
    op.drop_index(
        "spam_indicator_buckets_business_rule_window_idx",
        table_name="spam_indicator_buckets",
    )
    op.drop_index("spam_indicator_buckets_unique", table_name="spam_indicator_buckets")
    op.drop_table("spam_indicator_buckets")
