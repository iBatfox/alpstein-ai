"""message inbound idempotency — conversation-scoped dedup (E2.3)

Revision ID: 0010
Revises: 0009
Create Date: 2026-05-28
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_INCOMING_CUSTOMER_WHERE = sa.text(
    "external_message_id IS NOT NULL "
    "AND sender_type = 'customer' "
    "AND direction = 'incoming'"
)

_INCOMING_CUSTOMER_IDEMPOTENCY_WHERE = sa.text(
    "idempotency_key IS NOT NULL "
    "AND sender_type = 'customer' "
    "AND direction = 'incoming'"
)


def upgrade() -> None:
    op.add_column(
        "messages",
        sa.Column("idempotency_key", sa.String(length=255), nullable=True),
    )

    connection = op.get_bind()
    connection.execute(
        sa.text(
            """
            UPDATE messages
            SET idempotency_key = 'ext:' || external_message_id
            WHERE external_message_id IS NOT NULL
              AND sender_type = 'customer'
              AND direction = 'incoming'
              AND idempotency_key IS NULL
            """
        )
    )

    op.drop_index(
        "messages_business_external_message_id_unique",
        table_name="messages",
        postgresql_where=sa.text("external_message_id IS NOT NULL"),
    )

    op.create_index(
        "messages_incoming_conversation_external_unique",
        "messages",
        ["business_id", "conversation_id", "external_message_id"],
        unique=True,
        postgresql_where=_INCOMING_CUSTOMER_WHERE,
    )
    op.create_index(
        "messages_incoming_conversation_idempotency_unique",
        "messages",
        ["business_id", "conversation_id", "idempotency_key"],
        unique=True,
        postgresql_where=_INCOMING_CUSTOMER_IDEMPOTENCY_WHERE,
    )
    op.create_index(
        "messages_idempotency_key_idx",
        "messages",
        ["idempotency_key"],
        postgresql_where=sa.text("idempotency_key IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("messages_idempotency_key_idx", table_name="messages")
    op.drop_index(
        "messages_incoming_conversation_idempotency_unique",
        table_name="messages",
        postgresql_where=_INCOMING_CUSTOMER_IDEMPOTENCY_WHERE,
    )
    op.drop_index(
        "messages_incoming_conversation_external_unique",
        table_name="messages",
        postgresql_where=_INCOMING_CUSTOMER_WHERE,
    )

    op.create_index(
        "messages_business_external_message_id_unique",
        "messages",
        ["business_id", "external_message_id"],
        unique=True,
        postgresql_where=sa.text("external_message_id IS NOT NULL"),
    )

    op.drop_column("messages", "idempotency_key")
