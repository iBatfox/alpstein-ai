"""create_business_context_builder_tables

Revision ID: 0023
Revises: 0022
Create Date: 2026-06-08
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0023"
down_revision: str | None = "0022"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "business_context_builder"


def upgrade() -> None:
    op.execute(sa.text("CREATE SCHEMA IF NOT EXISTS business_context_builder"))
    op.create_table(
        "sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("business_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("telegram_user_id", sa.Text(), nullable=True),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "status",
            sa.String(length=50),
            nullable=False,
            server_default="in_progress",
        ),
        sa.Column("current_step", sa.String(length=100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=False),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=False),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=False), nullable=True),
        sa.CheckConstraint(
            "status IN ('created', 'in_progress', 'completed', 'archived')",
            name="business_context_builder_sessions_status_check",
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "bcb_sessions_tenant_id_idx",
        "sessions",
        ["tenant_id"],
        schema=SCHEMA,
    )
    op.create_index(
        "bcb_sessions_business_id_idx",
        "sessions",
        ["business_id"],
        schema=SCHEMA,
    )
    op.create_index(
        "bcb_sessions_tenant_business_idx",
        "sessions",
        ["tenant_id", "business_id"],
        schema=SCHEMA,
    )
    op.create_index(
        "bcb_sessions_tenant_business_status_idx",
        "sessions",
        ["tenant_id", "business_id", "status"],
        schema=SCHEMA,
    )

    op.create_table(
        "messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("business_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=False),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "role IN ('assistant', 'user', 'system')",
            name="business_context_builder_messages_role_check",
        ),
        sa.ForeignKeyConstraint(["session_id"], [f"{SCHEMA}.sessions.id"]),
        schema=SCHEMA,
    )
    op.create_index(
        "bcb_messages_tenant_id_idx",
        "messages",
        ["tenant_id"],
        schema=SCHEMA,
    )
    op.create_index(
        "bcb_messages_business_id_idx",
        "messages",
        ["business_id"],
        schema=SCHEMA,
    )
    op.create_index(
        "bcb_messages_tenant_business_session_idx",
        "messages",
        ["tenant_id", "business_id", "session_id"],
        schema=SCHEMA,
    )
    op.create_index(
        "bcb_messages_session_created_at_idx",
        "messages",
        ["session_id", "created_at"],
        schema=SCHEMA,
    )

    op.create_table(
        "results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("business_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("structured_context", postgresql.JSONB(), nullable=False),
        sa.Column("generated_prompt", sa.Text(), nullable=False),
        sa.Column("context_file_path", sa.Text(), nullable=True),
        sa.Column("context_file_url", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=False),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=False),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["session_id"], [f"{SCHEMA}.sessions.id"]),
        sa.UniqueConstraint(
            "session_id",
            name="business_context_builder_results_session_id_unique",
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "bcb_results_tenant_id_idx",
        "results",
        ["tenant_id"],
        schema=SCHEMA,
    )
    op.create_index(
        "bcb_results_business_id_idx",
        "results",
        ["business_id"],
        schema=SCHEMA,
    )
    op.create_index(
        "bcb_results_tenant_business_idx",
        "results",
        ["tenant_id", "business_id"],
        schema=SCHEMA,
    )
    op.create_index(
        "bcb_results_tenant_business_created_at_idx",
        "results",
        ["tenant_id", "business_id", "created_at"],
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_index(
        "bcb_results_tenant_business_created_at_idx",
        table_name="results",
        schema=SCHEMA,
    )
    op.drop_index(
        "bcb_results_tenant_business_idx",
        table_name="results",
        schema=SCHEMA,
    )
    op.drop_index(
        "bcb_results_business_id_idx",
        table_name="results",
        schema=SCHEMA,
    )
    op.drop_index(
        "bcb_results_tenant_id_idx",
        table_name="results",
        schema=SCHEMA,
    )
    op.drop_table("results", schema=SCHEMA)
    op.drop_index(
        "bcb_messages_session_created_at_idx",
        table_name="messages",
        schema=SCHEMA,
    )
    op.drop_index(
        "bcb_messages_tenant_business_session_idx",
        table_name="messages",
        schema=SCHEMA,
    )
    op.drop_index(
        "bcb_messages_business_id_idx",
        table_name="messages",
        schema=SCHEMA,
    )
    op.drop_index(
        "bcb_messages_tenant_id_idx",
        table_name="messages",
        schema=SCHEMA,
    )
    op.drop_table("messages", schema=SCHEMA)
    op.drop_index(
        "bcb_sessions_tenant_business_status_idx",
        table_name="sessions",
        schema=SCHEMA,
    )
    op.drop_index(
        "bcb_sessions_tenant_business_idx",
        table_name="sessions",
        schema=SCHEMA,
    )
    op.drop_index(
        "bcb_sessions_business_id_idx",
        table_name="sessions",
        schema=SCHEMA,
    )
    op.drop_index(
        "bcb_sessions_tenant_id_idx",
        table_name="sessions",
        schema=SCHEMA,
    )
    op.drop_table("sessions", schema=SCHEMA)
    op.execute(sa.text("DROP SCHEMA IF EXISTS business_context_builder"))
