"""Add ILB voice + rendered segment audio columns to courses.

ilb_voice_id (ElevenLabs voice) + ilb_segment_audio (per-segment narration audio URLs).
See docs/superpowers/specs/2026-05-21-ilb-design.md.

Revision ID: 009
Revises: 008
Create Date: 2026-05-23
"""
from alembic import op
import sqlalchemy as sa

revision = '009'
down_revision = '008'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('courses') as batch_op:
        batch_op.add_column(sa.Column('ilb_voice_id', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('ilb_segment_audio', sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('courses') as batch_op:
        batch_op.drop_column('ilb_segment_audio')
        batch_op.drop_column('ilb_voice_id')
