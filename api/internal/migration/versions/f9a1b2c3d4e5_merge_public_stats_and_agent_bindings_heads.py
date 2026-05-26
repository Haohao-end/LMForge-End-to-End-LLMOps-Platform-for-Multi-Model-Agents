"""merge public stats and agent bindings heads

Revision ID: f9a1b2c3d4e5
Revises: c3d4e5f6a7b8, e7f8a9b0c1d2
Create Date: 2026-05-26 16:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f9a1b2c3d4e5'
down_revision = ('c3d4e5f6a7b8', 'e7f8a9b0c1d2')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
