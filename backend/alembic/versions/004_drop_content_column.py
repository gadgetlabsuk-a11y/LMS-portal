"""Drop the retired courses.content column.

Revision ID: 004
Revises: 003
Create Date: 2026-05-09
"""
from alembic import op
import sqlalchemy as sa

revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # batch_alter_table required for SQLite DROP COLUMN
    with op.batch_alter_table('courses') as batch_op:
        batch_op.drop_column('content')


def downgrade() -> None:
    # Add content column back (empty — data not recoverable)
    with op.batch_alter_table('courses') as batch_op:
        batch_op.add_column(sa.Column('content', sa.JSON(), nullable=True))
