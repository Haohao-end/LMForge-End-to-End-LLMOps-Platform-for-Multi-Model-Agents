"""add mcp tool snapshots to app config tables

Revision ID: d1e2f3a4b5c6
Revises: a6d4c3b2e1f0
Create Date: 2026-05-21 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'd1e2f3a4b5c6'
down_revision = 'a6d4c3b2e1f0'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('app_config', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                'mcp_tool_snapshots',
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'[]'::jsonb"),
            )
        )

    with op.batch_alter_table('app_config_version', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                'mcp_tool_snapshots',
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'[]'::jsonb"),
            )
        )


def downgrade():
    with op.batch_alter_table('app_config_version', schema=None) as batch_op:
        batch_op.drop_column('mcp_tool_snapshots')

    with op.batch_alter_table('app_config', schema=None) as batch_op:
        batch_op.drop_column('mcp_tool_snapshots')
