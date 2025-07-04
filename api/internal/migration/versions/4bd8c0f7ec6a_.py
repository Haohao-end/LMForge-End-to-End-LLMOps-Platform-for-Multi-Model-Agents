"""empty message

Revision ID: 4bd8c0f7ec6a
Revises: dbbb4f3fe0c7
Create Date: 2025-06-09 21:53:36.693061

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4bd8c0f7ec6a'
down_revision = 'dbbb4f3fe0c7'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('app', schema=None) as batch_op:
        batch_op.add_column(sa.Column('token', sa.String(length=255), server_default=sa.text("''::character varying"), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('app', schema=None) as batch_op:
        batch_op.drop_column('token')

    # ### end Alembic commands ###
