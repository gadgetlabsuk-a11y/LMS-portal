"""Add ILB (Interactive Learning Broadcast) tables + Video avatar fields.

Creates broadcast_sessions, interactions, session_attestations; adds podcast/avatar
config columns to videos. Part of the ILB demo (see docs/superpowers/specs/2026-05-21-ilb-design.md).

Revision ID: 006
Revises: 005
Create Date: 2026-05-21
"""
from alembic import op
import sqlalchemy as sa

revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- videos: add ILB avatar/podcast config ---
    with op.batch_alter_table('videos') as batch_op:
        batch_op.add_column(sa.Column('heygen_avatar_id', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('prerendered_video_url', sa.String(length=500), nullable=True))

    # --- broadcast_sessions ---
    op.create_table(
        'broadcast_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('enrollment_id', sa.Integer(), sa.ForeignKey('enrollments.id', ondelete='CASCADE'), nullable=False),
        sa.Column('mode', sa.String(length=20), server_default='interrupt', nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('final_score', sa.Float(), nullable=True),
        sa.Column('completion_status', sa.String(length=20), server_default='in_progress', nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_broadcast_enrollment', 'broadcast_sessions', ['enrollment_id'])

    # --- interactions ---
    op.create_table(
        'interactions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('broadcast_session_id', sa.Integer(), sa.ForeignKey('broadcast_sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('ts', sa.DateTime(), nullable=False),
        sa.Column('type', sa.String(length=20), nullable=False),
        sa.Column('input_mode', sa.String(length=10), nullable=True),
        sa.Column('question_text', sa.Text(), nullable=True),
        sa.Column('answer_text', sa.Text(), nullable=True),
        sa.Column('source_refs', sa.JSON(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('escalated', sa.Boolean(), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_interaction_session_ts', 'interactions', ['broadcast_session_id', 'ts'])

    # --- session_attestations ---
    op.create_table(
        'session_attestations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('broadcast_session_id', sa.Integer(), sa.ForeignKey('broadcast_sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('learner_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('sequence', sa.Integer(), server_default='0', nullable=False),
        sa.Column('content_hash', sa.String(length=64), nullable=False),
        sa.Column('prev_hash', sa.String(length=64), nullable=True),
        sa.Column('signed_at', sa.DateTime(), nullable=False),
        sa.Column('timestamp_token', sa.Text(), nullable=True),
        sa.Column('anchor_ref', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_attestation_session', 'session_attestations', ['broadcast_session_id'])
    op.create_index('idx_attestation_learner_seq', 'session_attestations', ['learner_id', 'sequence'])


def downgrade() -> None:
    op.drop_index('idx_attestation_learner_seq', table_name='session_attestations')
    op.drop_index('idx_attestation_session', table_name='session_attestations')
    op.drop_table('session_attestations')

    op.drop_index('idx_interaction_session_ts', table_name='interactions')
    op.drop_table('interactions')

    op.drop_index('idx_broadcast_enrollment', table_name='broadcast_sessions')
    op.drop_table('broadcast_sessions')

    with op.batch_alter_table('videos') as batch_op:
        batch_op.drop_column('prerendered_video_url')
        batch_op.drop_column('heygen_avatar_id')
