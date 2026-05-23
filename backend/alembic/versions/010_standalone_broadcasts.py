"""Standalone broadcasts: broadcasts table + broadcast_sessions linkage.

Adds the standalone Broadcast entity (org content outside a course) and lets a
BroadcastSession be backed by EITHER a course enrolment OR a standalone broadcast
(enrollment_id becomes nullable; add broadcast_id + learner_id).
See docs/superpowers/specs/2026-05-21-ilb-design.md.

Revision ID: 010
Revises: 009
Create Date: 2026-05-23
"""
from alembic import op
import sqlalchemy as sa

revision = '010'
down_revision = '009'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'broadcasts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('creator_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('source_text', sa.Text(), nullable=True),
        sa.Column('host_persona', sa.String(length=255), nullable=True),
        sa.Column('avatar_id', sa.String(length=100), nullable=True),
        sa.Column('voice_id', sa.String(length=100), nullable=True),
        sa.Column('script', sa.Text(), nullable=True),
        sa.Column('segments', sa.JSON(), nullable=True),
        sa.Column('segment_audio', sa.JSON(), nullable=True),
        sa.Column('published', sa.Boolean(), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_broadcast_creator', 'broadcasts', ['creator_id'])

    with op.batch_alter_table('broadcast_sessions') as batch_op:
        batch_op.alter_column('enrollment_id', existing_type=sa.Integer(), nullable=True)
        batch_op.add_column(sa.Column('broadcast_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('learner_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_bsession_broadcast', 'broadcasts', ['broadcast_id'], ['id'], ondelete='CASCADE')
        batch_op.create_foreign_key('fk_bsession_learner', 'users', ['learner_id'], ['id'], ondelete='SET NULL')
        batch_op.create_index('idx_broadcast_session_broadcast', ['broadcast_id'])


def downgrade() -> None:
    with op.batch_alter_table('broadcast_sessions') as batch_op:
        batch_op.drop_index('idx_broadcast_session_broadcast')
        batch_op.drop_constraint('fk_bsession_learner', type_='foreignkey')
        batch_op.drop_constraint('fk_bsession_broadcast', type_='foreignkey')
        batch_op.drop_column('learner_id')
        batch_op.drop_column('broadcast_id')
        batch_op.alter_column('enrollment_id', existing_type=sa.Integer(), nullable=False)

    op.drop_index('idx_broadcast_creator', table_name='broadcasts')
    op.drop_table('broadcasts')
