"""add agent bindings to app config tables

Revision ID: e7f8a9b0c1d2
Revises: d1e2f3a4b5c6
Create Date: 2026-05-23 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'e7f8a9b0c1d2'
down_revision = 'd1e2f3a4b5c6'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('app_config', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                'agent_bindings',
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'[]'::jsonb"),
            )
        )

    with op.batch_alter_table('app_config_version', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                'agent_bindings',
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'[]'::jsonb"),
            )
        )


def downgrade():
    with op.batch_alter_table('app_config_version', schema=None) as batch_op:
        batch_op.drop_column('agent_bindings')

    with op.batch_alter_table('app_config', schema=None) as batch_op:
        batch_op.drop_column('agent_bindings')
