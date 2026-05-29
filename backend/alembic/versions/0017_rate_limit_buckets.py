"""rate_limit_buckets — E3.5a ingress rate counter buckets

Revision ID: 0017
Revises: 0016
Create Date: 2026-05-28
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0017"
down_revision: str | None = "0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "rate_limit_buckets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("business_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scope_type", sa.String(length=50), nullable=False),
        sa.Column("scope_key", sa.String(length=255), nullable=False),
        sa.Column("channel", sa.String(length=50), nullable=True),
        sa.Column("window_start", sa.DateTime(timezone=False), nullable=False),
        sa.Column("window_seconds", sa.Integer(), nullable=False),
        sa.Column("request_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=False), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=False), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"]),
    )
    op.create_index(
        "rate_limit_buckets_scope_window_unique",
        "rate_limit_buckets",
        ["tenant_id", "business_id", "scope_type", "scope_key", "window_start"],
        unique=True,
    )
    op.create_index(
        "rate_limit_buckets_business_scope_window_idx",
        "rate_limit_buckets",
        ["business_id", "scope_type", "window_start"],
    )
    op.create_index("rate_limit_buckets_tenant_id_idx", "rate_limit_buckets", ["tenant_id"])
    op.create_index(
        "rate_limit_buckets_business_id_idx",
        "rate_limit_buckets",
        ["business_id"],
    )


def downgrade() -> None:
    op.drop_index("rate_limit_buckets_business_id_idx", table_name="rate_limit_buckets")
    op.drop_index("rate_limit_buckets_tenant_id_idx", table_name="rate_limit_buckets")
    op.drop_index(
        "rate_limit_buckets_business_scope_window_idx",
        table_name="rate_limit_buckets",
    )
    op.drop_index(
        "rate_limit_buckets_scope_window_unique",
        table_name="rate_limit_buckets",
    )
    op.drop_table("rate_limit_buckets")
