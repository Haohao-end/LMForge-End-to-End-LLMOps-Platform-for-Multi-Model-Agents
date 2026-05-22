"""add mcp bindings to app config tables

Revision ID: c8d9e0f1a2b3
Revises: f2c7b8d91e34
Create Date: 2026-05-18 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'c8d9e0f1a2b3'
down_revision = 'f2c7b8d91e34'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('app_config', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                'mcp_bindings',
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'[]'::jsonb"),
            )
        )

    with op.batch_alter_table('app_config_version', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                'mcp_bindings',
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'[]'::jsonb"),
            )
        )


def downgrade():
    with op.batch_alter_table('app_config_version', schema=None) as batch_op:
        batch_op.drop_column('mcp_bindings')

    with op.batch_alter_table('app_config', schema=None) as batch_op:
        batch_op.drop_column('mcp_bindings')
