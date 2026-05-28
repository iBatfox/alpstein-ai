"""create flows table and backfill default flows per business

Revision ID: 0008
Revises: 0007
Create Date: 2026-05-28
"""

from collections.abc import Sequence
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Deterministic flow ids for known demo businesses (E2.1).
FLOW_ID_BARBERSHOP = uuid.UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaa10")
FLOW_ID_ALPSTEIN = uuid.UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaa11")
BUSINESS_ID_BARBERSHOP = uuid.UUID("22222222-2222-4222-8222-222222222222")
BUSINESS_ID_ALPSTEIN = uuid.UUID("22222222-2222-4222-8222-222222222223")
TENANT_ID_DEMO = uuid.UUID("11111111-1111-4111-8111-111111111111")

KNOWN_DEMO_FLOWS: tuple[tuple[uuid.UUID, uuid.UUID, uuid.UUID, str, str], ...] = (
    (
        FLOW_ID_BARBERSHOP,
        TENANT_ID_DEMO,
        BUSINESS_ID_BARBERSHOP,
        "barbershop_default",
        "Barbershop demo flow",
    ),
    (
        FLOW_ID_ALPSTEIN,
        TENANT_ID_DEMO,
        BUSINESS_ID_ALPSTEIN,
        "default",
        "Alpstein AI demo flow",
    ),
)


def _flow_id_for_business(business_id: uuid.UUID) -> uuid.UUID:
    return uuid.uuid5(uuid.NAMESPACE_URL, f"alpstein-ai:flow:default:{business_id}")


def upgrade() -> None:
    op.create_table(
        "flows",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("business_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("flow_key", sa.String(length=100), nullable=False),
        sa.Column("flow_name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="active"),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "business_id",
            "flow_key",
            name="flows_business_flow_key_unique",
        ),
    )
    op.create_index("flows_tenant_id_idx", "flows", ["tenant_id"])
    op.create_index("flows_business_id_idx", "flows", ["business_id"])
    op.create_index("flows_status_idx", "flows", ["status"])
    op.create_index(
        "flows_business_default_unique",
        "flows",
        ["business_id"],
        unique=True,
        postgresql_where=sa.text("is_default = true"),
    )

    connection = op.get_bind()
    businesses = connection.execute(
        sa.text("SELECT id, tenant_id, external_id FROM businesses")
    ).fetchall()

    for business_id, tenant_id, external_id in businesses:
        if business_id in {row[2] for row in KNOWN_DEMO_FLOWS}:
            for flow_id, t_id, b_id, flow_key, flow_name in KNOWN_DEMO_FLOWS:
                if b_id == business_id:
                    connection.execute(
                        sa.text(
                            """
                            INSERT INTO flows (
                                id, tenant_id, business_id, flow_key, flow_name,
                                status, is_default, created_at, updated_at
                            ) VALUES (
                                :id, :tenant_id, :business_id, :flow_key, :flow_name,
                                'active', true, NOW(), NOW()
                            )
                            ON CONFLICT (business_id, flow_key) DO NOTHING
                            """
                        ),
                        {
                            "id": flow_id,
                            "tenant_id": t_id,
                            "business_id": b_id,
                            "flow_key": flow_key,
                            "flow_name": flow_name,
                        },
                    )
                    break
            continue

        flow_id = _flow_id_for_business(business_id)
        flow_key = "default"
        flow_name = f"Default flow ({external_id})"
        connection.execute(
            sa.text(
                """
                INSERT INTO flows (
                    id, tenant_id, business_id, flow_key, flow_name,
                    status, is_default, created_at, updated_at
                ) VALUES (
                    :id, :tenant_id, :business_id, :flow_key, :flow_name,
                    'active', true, NOW(), NOW()
                )
                ON CONFLICT (business_id, flow_key) DO NOTHING
                """
            ),
            {
                "id": flow_id,
                "tenant_id": tenant_id,
                "business_id": business_id,
                "flow_key": flow_key,
                "flow_name": flow_name,
            },
        )


def downgrade() -> None:
    op.drop_index("flows_business_default_unique", table_name="flows")
    op.drop_index("flows_status_idx", table_name="flows")
    op.drop_index("flows_business_id_idx", table_name="flows")
    op.drop_index("flows_tenant_id_idx", table_name="flows")
    op.drop_table("flows")
