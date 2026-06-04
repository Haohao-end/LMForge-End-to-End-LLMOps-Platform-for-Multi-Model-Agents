"""drop public sharing stats tables and counters

Revision ID: c3d4e5f6a7b8
Revises: a1b2c3d4e5f6
Create Date: 2026-05-23 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'c3d4e5f6a7b8'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def _drop_table_if_exists(table_name: str) -> None:
    op.drop_table(table_name, if_exists=True)


def _drop_index_if_exists(index_name: str, table_name: str) -> None:
    op.drop_index(index_name, table_name=table_name, if_exists=True)


def _drop_columns_if_exist(table_name: str, *column_names: str) -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(table_name):
        return

    existing_columns = {column["name"] for column in inspector.get_columns(table_name)}
    for column_name in column_names:
        if column_name in existing_columns:
            op.drop_column(table_name, column_name)


def upgrade():
    # 1. 删除公开统计关联表
    _drop_table_if_exists('workflow_favorite')
    _drop_table_if_exists('workflow_like')
    _drop_table_if_exists('app_favorite')
    _drop_table_if_exists('app_like')

    # 2. 删除 workflow 表上的统计列和统计索引
    _drop_index_if_exists('workflow_like_count_idx', 'workflow')
    _drop_columns_if_exist('workflow', 'fork_count', 'like_count', 'view_count')

    # 3. 删除 app 表上的统计列和统计索引
    _drop_index_if_exists('app_like_count_idx', 'app')
    _drop_columns_if_exist('app', 'fork_count', 'like_count', 'view_count')


def downgrade():
    # 1. 恢复 app 表统计列
    with op.batch_alter_table('app', schema=None) as batch_op:
        batch_op.add_column(sa.Column('view_count', sa.Integer(), nullable=False, server_default=sa.text('0')))
        batch_op.add_column(sa.Column('like_count', sa.Integer(), nullable=False, server_default=sa.text('0')))
        batch_op.add_column(sa.Column('fork_count', sa.Integer(), nullable=False, server_default=sa.text('0')))
        batch_op.create_index('app_like_count_idx', ['like_count'])

    # 2. 恢复 workflow 表统计列
    with op.batch_alter_table('workflow', schema=None) as batch_op:
        batch_op.add_column(sa.Column('view_count', sa.Integer(), nullable=False, server_default=sa.text('0')))
        batch_op.add_column(sa.Column('like_count', sa.Integer(), nullable=False, server_default=sa.text('0')))
        batch_op.add_column(sa.Column('fork_count', sa.Integer(), nullable=False, server_default=sa.text('0')))
        batch_op.create_index('workflow_like_count_idx', ['like_count'])

    # 3. 恢复公开统计关联表
    op.create_table(
        'app_like',
        sa.Column('id', sa.UUID(), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('app_id', sa.UUID(), nullable=False),
        sa.Column('account_id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP(0)'), nullable=False),
        sa.PrimaryKeyConstraint('id', name='pk_app_like_id'),
        sa.UniqueConstraint('app_id', 'account_id', name='uq_app_like_app_account'),
    )
    op.create_index('app_like_app_id_idx', 'app_like', ['app_id'])
    op.create_index('app_like_account_id_idx', 'app_like', ['account_id'])

    op.create_table(
        'app_favorite',
        sa.Column('id', sa.UUID(), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('app_id', sa.UUID(), nullable=False),
        sa.Column('account_id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP(0)'), nullable=False),
        sa.PrimaryKeyConstraint('id', name='pk_app_favorite_id'),
        sa.UniqueConstraint('app_id', 'account_id', name='uq_app_favorite_app_account'),
    )
    op.create_index('app_favorite_app_id_idx', 'app_favorite', ['app_id'])
    op.create_index('app_favorite_account_id_idx', 'app_favorite', ['account_id'])

    op.create_table(
        'workflow_like',
        sa.Column('id', sa.UUID(), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('workflow_id', sa.UUID(), nullable=False),
        sa.Column('account_id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP(0)'), nullable=False),
        sa.PrimaryKeyConstraint('id', name='pk_workflow_like_id'),
        sa.UniqueConstraint('workflow_id', 'account_id', name='uq_workflow_like_workflow_account'),
    )
    op.create_index('workflow_like_workflow_id_idx', 'workflow_like', ['workflow_id'])
    op.create_index('workflow_like_account_id_idx', 'workflow_like', ['account_id'])

    op.create_table(
        'workflow_favorite',
        sa.Column('id', sa.UUID(), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('workflow_id', sa.UUID(), nullable=False),
        sa.Column('account_id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP(0)'), nullable=False),
        sa.PrimaryKeyConstraint('id', name='pk_workflow_favorite_id'),
        sa.UniqueConstraint('workflow_id', 'account_id', name='uq_workflow_favorite_workflow_account'),
    )
    op.create_index('workflow_favorite_workflow_id_idx', 'workflow_favorite', ['workflow_id'])
    op.create_index('workflow_favorite_account_id_idx', 'workflow_favorite', ['account_id'])
