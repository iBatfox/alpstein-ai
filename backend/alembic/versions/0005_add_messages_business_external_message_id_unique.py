"""add messages business external_message_id unique index

Revision ID: 0005
Revises: 0004
Create Date: 2026-05-24
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "messages_business_external_message_id_unique",
        "messages",
        ["business_id", "external_message_id"],
        unique=True,
        postgresql_where=sa.text("external_message_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "messages_business_external_message_id_unique",
        table_name="messages",
        postgresql_where=sa.text("external_message_id IS NOT NULL"),
    )
