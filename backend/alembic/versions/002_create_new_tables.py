"""Create all new relational tables for AI Course Builder.

Revision ID: 002
Revises: 001
Create Date: 2026-05-09
"""
from alembic import op
import sqlalchemy as sa

revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'modules',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('course_id', sa.Integer(), sa.ForeignKey('courses.id', ondelete='CASCADE'), nullable=False),
        sa.Column('order_index', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('learning_objectives', sa.JSON(), nullable=True),
        sa.Column('estimated_duration_minutes', sa.Integer(), nullable=True),
        sa.Column('pass_rate_override', sa.Integer(), nullable=True),
        sa.Column('unlock_rule', sa.String(50), nullable=True, server_default='after_previous'),
        sa.Column('unlock_days_after_enrolment', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(20), nullable=True, server_default='draft'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_module_course_order', 'modules', ['course_id', 'order_index'])

    op.create_table(
        'videos',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('module_id', sa.Integer(), sa.ForeignKey('modules.id', ondelete='CASCADE'), nullable=False),
        sa.Column('order_index', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('video_type', sa.String(50), nullable=False, server_default='slideshow_narrated'),
        sa.Column('estimated_duration_seconds', sa.Integer(), nullable=True),
        sa.Column('narration_voice_id', sa.String(100), nullable=True),
        sa.Column('source_video_url', sa.String(500), nullable=True),
        sa.Column('status', sa.String(20), nullable=True, server_default='draft'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_video_module_order', 'videos', ['module_id', 'order_index'])

    op.create_table(
        'slides',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('video_id', sa.Integer(), sa.ForeignKey('videos.id', ondelete='CASCADE'), nullable=False),
        sa.Column('order_index', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('layout_id', sa.String(50), nullable=True),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('narration_script', sa.Text(), nullable=True),
        sa.Column('narration_audio_url', sa.String(500), nullable=True),
        sa.Column('narration_script_hash', sa.String(64), nullable=True),
        sa.Column('transition', sa.String(20), nullable=True, server_default='none'),
        sa.Column('status', sa.String(20), nullable=True, server_default='draft'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_slide_video_order', 'slides', ['video_id', 'order_index'])

    op.create_table(
        'blocks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('slide_id', sa.Integer(), sa.ForeignKey('slides.id', ondelete='CASCADE'), nullable=False),
        sa.Column('order_index', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('type', sa.String(50), nullable=False),
        sa.Column('content', sa.JSON(), nullable=True),
        sa.Column('style', sa.JSON(), nullable=True),
        sa.Column('alt_text', sa.String(500), nullable=True),
        sa.Column('grid_position', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_block_slide_order', 'blocks', ['slide_id', 'order_index'])

    op.create_table(
        'quizzes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('module_id', sa.Integer(), sa.ForeignKey('modules.id', ondelete='CASCADE'), nullable=True),
        sa.Column('video_id', sa.Integer(), sa.ForeignKey('videos.id', ondelete='CASCADE'), nullable=True),
        sa.Column('order_index', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('quiz_type', sa.String(50), nullable=False, server_default='knowledge_check'),
        sa.Column('pass_rate', sa.Integer(), nullable=False, server_default='80'),
        sa.Column('attempts_allowed', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('time_limit_seconds', sa.Integer(), nullable=True),
        sa.Column('shuffle_questions', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('show_feedback', sa.String(20), nullable=False, server_default='immediate'),
        sa.Column('on_fail_action', sa.String(20), nullable=False, server_default='retake'),
        sa.Column('status', sa.String(20), nullable=True, server_default='draft'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_quiz_module', 'quizzes', ['module_id'])

    op.create_table(
        'questions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('quiz_id', sa.Integer(), sa.ForeignKey('quizzes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('order_index', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('type', sa.String(50), nullable=False),
        sa.Column('prompt', sa.Text(), nullable=False),
        sa.Column('points', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('explanation', sa.Text(), nullable=True),
        sa.Column('options', sa.JSON(), nullable=True),
        sa.Column('correct_answer', sa.JSON(), nullable=True),
        sa.Column('linked_objective_id', sa.Integer(), nullable=True),
        sa.Column('difficulty', sa.String(20), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_question_quiz_order', 'questions', ['quiz_id', 'order_index'])

    op.create_table(
        'resources',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('module_id', sa.Integer(), sa.ForeignKey('modules.id', ondelete='CASCADE'), nullable=False),
        sa.Column('type', sa.String(50), nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('url_or_file', sa.String(500), nullable=False),
        sa.Column('visible_to_learner', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_resource_module', 'resources', ['module_id'])

    op.create_table(
        'ai_prompt_log',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('creator_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('operation', sa.String(100), nullable=False),
        sa.Column('inputs', sa.JSON(), nullable=True),
        sa.Column('output', sa.Text(), nullable=True),
        sa.Column('model_tier', sa.String(50), nullable=True),
        sa.Column('tokens_used', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_ai_log_creator_created', 'ai_prompt_log', ['creator_id', 'created_at'])
    op.create_index('idx_ai_log_created_at', 'ai_prompt_log', ['created_at'])


def downgrade() -> None:
    # Drop in reverse FK dependency order
    op.drop_table('ai_prompt_log')
    op.drop_table('resources')
    op.drop_table('questions')
    op.drop_table('quizzes')
    op.drop_table('blocks')
    op.drop_table('slides')
    op.drop_table('videos')
    op.drop_table('modules')
