"""Add quiz_attempts (learner quiz scoring).

Revision ID: 015
Revises: 014
Create Date: 2026-05-26
"""
from alembic import op
import sqlalchemy as sa

revision = '015'
down_revision = '014'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'quiz_attempts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('quiz_id', sa.Integer(), sa.ForeignKey('quizzes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('attempt_number', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('score', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('passed', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('answers', sa.JSON(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('submitted_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_quiz_attempt_user_quiz', 'quiz_attempts', ['user_id', 'quiz_id'])


def downgrade() -> None:
    op.drop_index('idx_quiz_attempt_user_quiz', table_name='quiz_attempts')
    op.drop_table('quiz_attempts')
