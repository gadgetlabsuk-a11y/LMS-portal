"""Add course-level ILB (Interactive Learning Broadcast) config columns.

ilb_script / host_persona / avatar_id / segments / published — persist a course's broadcast
so the player can load it and learners only see published broadcasts.
See docs/superpowers/specs/2026-05-21-ilb-design.md.

Revision ID: 008
Revises: 007
Create Date: 2026-05-23
"""
from alembic import op
import sqlalchemy as sa

revision = '008'
down_revision = '007'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('courses') as batch_op:
        batch_op.add_column(sa.Column('ilb_script', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('ilb_host_persona', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('ilb_avatar_id', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('ilb_segments', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('ilb_published', sa.Boolean(), server_default='0', nullable=False))


def downgrade() -> None:
    with op.batch_alter_table('courses') as batch_op:
        batch_op.drop_column('ilb_published')
        batch_op.drop_column('ilb_segments')
        batch_op.drop_column('ilb_avatar_id')
        batch_op.drop_column('ilb_host_persona')
        batch_op.drop_column('ilb_script')
