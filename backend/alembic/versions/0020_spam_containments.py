"""spam_containments — E3.6b reversible spam containment state

Revision ID: 0020
Revises: 0019
Create Date: 2026-05-28
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0020"
down_revision: str | None = "0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "spam_containments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("business_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rule_id", sa.String(length=64), nullable=False),
        sa.Column("scope_type", sa.String(length=32), nullable=False),
        sa.Column("scope_key", sa.String(length=255), nullable=False),
        sa.Column("channel", sa.String(length=50), nullable=True),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=False), nullable=False),
        sa.Column("released_at", sa.DateTime(timezone=False), nullable=True),
        sa.Column("correlation_id", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=False), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"]),
    )
    op.create_index(
        "spam_containments_active_unique",
        "spam_containments",
        ["tenant_id", "business_id", "scope_type", "scope_key", "rule_id"],
        unique=True,
        postgresql_where=sa.text("released_at IS NULL"),
    )
    op.create_index(
        "spam_containments_business_channel_expires_idx",
        "spam_containments",
        ["business_id", "channel", "expires_at"],
    )
    op.create_index("spam_containments_tenant_id_idx", "spam_containments", ["tenant_id"])
    op.create_index(
        "spam_containments_business_id_idx",
        "spam_containments",
        ["business_id"],
    )
    op.create_index(
        "spam_containments_conversation_id_idx",
        "spam_containments",
        ["conversation_id"],
    )


def downgrade() -> None:
    op.drop_index("spam_containments_conversation_id_idx", table_name="spam_containments")
    op.drop_index("spam_containments_business_id_idx", table_name="spam_containments")
    op.drop_index("spam_containments_tenant_id_idx", table_name="spam_containments")
    op.drop_index(
        "spam_containments_business_channel_expires_idx",
        table_name="spam_containments",
    )
    op.drop_index("spam_containments_active_unique", table_name="spam_containments")
    op.drop_table("spam_containments")
