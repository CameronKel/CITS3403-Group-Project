"""add achievement_key to feed_posts

Revision ID: a7c2f1d9b3e4
Revises: 9e5df8f207e3
Create Date: 2026-05-17 19:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a7c2f1d9b3e4'
down_revision = '9e5df8f207e3'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('feed_posts', schema=None) as batch_op:
        batch_op.add_column(sa.Column('achievement_key', sa.String(length=64), nullable=True))


def downgrade():
    with op.batch_alter_table('feed_posts', schema=None) as batch_op:
        batch_op.drop_column('achievement_key')
