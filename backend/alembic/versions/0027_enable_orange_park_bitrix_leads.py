"""Enable Bitrix24 lead sync for Orange Park flows.

Revision ID: 0027
Revises: 0026
"""

from alembic import op

revision = "0027"
down_revision = "0026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        update flows as f
        set metadata = coalesce(f.metadata, '{}'::jsonb) || jsonb_build_object(
            'crm',
            coalesce(f.metadata->'crm', '{}'::jsonb) || jsonb_build_object(
                'bitrix',
                coalesce(f.metadata->'crm'->'bitrix', '{}'::jsonb)
                    || '{"enabled": true}'::jsonb
            )
        )
        from businesses as b
        where b.id = f.business_id
          and b.external_id = 'orange-park'
        """
    )


def downgrade() -> None:
    op.execute(
        """
        update flows as f
        set metadata = coalesce(f.metadata, '{}'::jsonb) || jsonb_build_object(
            'crm',
            coalesce(f.metadata->'crm', '{}'::jsonb) || jsonb_build_object(
                'bitrix',
                coalesce(f.metadata->'crm'->'bitrix', '{}'::jsonb) - 'enabled'
            )
        )
        from businesses as b
        where b.id = f.business_id
          and b.external_id = 'orange-park'
        """
    )
