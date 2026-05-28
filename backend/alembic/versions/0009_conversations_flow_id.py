"""conversations flow_id — E2.2 flow-scoped lookup

Revision ID: 0009
Revises: 0008
Create Date: 2026-05-28
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "conversations",
        sa.Column("flow_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "conversations_flow_id_fkey",
        "conversations",
        "flows",
        ["flow_id"],
        ["id"],
    )

    connection = op.get_bind()
    connection.execute(
        sa.text(
            """
            UPDATE conversations AS c
            SET flow_id = f.id
            FROM flows AS f
            WHERE f.business_id = c.business_id
              AND f.is_default = true
              AND c.flow_id IS NULL
            """
        )
    )

    op.alter_column("conversations", "flow_id", nullable=False)

    op.create_index("conversations_flow_id_idx", "conversations", ["flow_id"])
    op.create_index(
        "conversations_flow_channel_external_idx",
        "conversations",
        ["flow_id", "channel", "external_conversation_id"],
        postgresql_where=sa.text("external_conversation_id IS NOT NULL"),
    )
    op.create_index(
        "conversations_flow_channel_customer_idx",
        "conversations",
        ["flow_id", "channel", "customer_id"],
    )


def downgrade() -> None:
    op.drop_index("conversations_flow_channel_customer_idx", table_name="conversations")
    op.drop_index("conversations_flow_channel_external_idx", table_name="conversations")
    op.drop_index("conversations_flow_id_idx", table_name="conversations")
    op.drop_constraint("conversations_flow_id_fkey", "conversations", type_="foreignkey")
    op.drop_column("conversations", "flow_id")
