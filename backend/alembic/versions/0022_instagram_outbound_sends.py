"""instagram_outbound_sends — idempotency for Meta Instagram outbound replies

Revision ID: 0022
Revises: 0021
Create Date: 2026-05-31
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0022"
down_revision: str | None = "0021"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "instagram_outbound_sends",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("business_external_id", sa.String(length=128), nullable=False),
        sa.Column("external_inbound_message_id", sa.String(length=255), nullable=False),
        sa.Column("provider_message_id", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=False),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint(
            "business_external_id",
            "external_inbound_message_id",
            name="instagram_outbound_sends_business_inbound_unique",
        ),
    )
    op.create_index(
        "instagram_outbound_sends_created_at_idx",
        "instagram_outbound_sends",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "instagram_outbound_sends_created_at_idx",
        table_name="instagram_outbound_sends",
    )
    op.drop_table("instagram_outbound_sends")
