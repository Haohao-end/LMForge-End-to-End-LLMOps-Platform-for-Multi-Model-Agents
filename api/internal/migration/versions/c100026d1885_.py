"""empty message

Revision ID: c100026d1885
Revises: ab0fba23ea27
Create Date: 2025-05-24 22:09:16.508594

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c100026d1885'
down_revision = 'ab0fba23ea27'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('api_key',
    sa.Column('id', sa.UUID(), server_default=sa.text('uuid_generate_v4()'), nullable=False),
    sa.Column('account_id', sa.UUID(), nullable=False),
    sa.Column('api_key', sa.String(length=255), server_default=sa.text("''::character varying"), nullable=False),
    sa.Column('is_active', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('remark', sa.String(length=255), server_default=sa.text("''::character varying"), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP(0)'), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP(0)'), nullable=False),
    sa.PrimaryKeyConstraint('id', name='pk_api_key_id')
    )
    op.create_table('end_user',
    sa.Column('id', sa.UUID(), server_default=sa.text('uuid_generate_v4()'), nullable=False),
    sa.Column('tenant_id', sa.UUID(), nullable=False),
    sa.Column('app_id', sa.UUID(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP(0)'), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP(0)'), nullable=False),
    sa.PrimaryKeyConstraint('id', name='pk_end_user_id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('end_user')
    op.drop_table('api_key')
    # ### end Alembic commands ###
