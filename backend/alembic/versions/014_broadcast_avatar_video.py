"""Add Broadcast.segment_video + video_render_jobs (HeyGen pre-rendered avatar).

Revision ID: 014
Revises: 013
Create Date: 2026-05-25
"""
from alembic import op
import sqlalchemy as sa

revision = '014'
down_revision = '013'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('broadcasts') as batch_op:
        batch_op.add_column(sa.Column('segment_video', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('video_render_jobs', sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('broadcasts') as batch_op:
        batch_op.drop_column('video_render_jobs')
        batch_op.drop_column('segment_video')
