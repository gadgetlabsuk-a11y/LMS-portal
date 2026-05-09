"""Extend courses table with new columns for AI Course Builder.

Revision ID: 001
Revises:
Create Date: 2026-05-09
"""
from alembic import op
import sqlalchemy as sa

revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new columns to courses — all nullable/defaulted, zero data risk
    op.add_column('courses', sa.Column('slug', sa.String(200), nullable=True))
    op.add_column('courses', sa.Column('summary', sa.Text(), nullable=True))
    op.add_column('courses', sa.Column('thumbnail_url', sa.String(500), nullable=True))
    op.add_column('courses', sa.Column('audience_level', sa.String(50), nullable=True))
    op.add_column('courses', sa.Column('learning_objectives', sa.JSON(), nullable=True))
    op.add_column('courses', sa.Column('category', sa.String(100), nullable=True))
    op.add_column('courses', sa.Column('tags', sa.JSON(), nullable=True))
    op.add_column('courses', sa.Column('estimated_duration_minutes', sa.Integer(), nullable=True))
    op.add_column('courses', sa.Column('ai_tone_preset', sa.String(50), nullable=True))
    op.add_column('courses', sa.Column('ai_custom_prompt', sa.Text(), nullable=True))
    op.add_column('courses', sa.Column('navigation_mode', sa.String(20), nullable=True, server_default='sequential'))
    op.add_column('courses', sa.Column('default_pass_rate', sa.Integer(), nullable=True, server_default='80'))
    op.add_column('courses', sa.Column('default_quiz_attempts', sa.Integer(), nullable=True, server_default='3'))
    op.add_column('courses', sa.Column('default_quiz_time_limit_seconds', sa.Integer(), nullable=True))
    op.add_column('courses', sa.Column('certificate_enabled', sa.Boolean(), nullable=True, server_default='1'))
    op.add_column('courses', sa.Column('published_at', sa.DateTime(), nullable=True))
    op.add_column('courses', sa.Column('version', sa.Integer(), nullable=True, server_default='1'))

    # Extend CourseStatus enum with has_unpublished_changes
    # SQLite: server_default covers it; PostgreSQL: must ALTER TYPE outside transaction
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        with op.get_context().autocommit_block():
            op.execute("ALTER TYPE coursestatus ADD VALUE IF NOT EXISTS 'has_unpublished_changes'")

    # Add course_version to enrollments for learner progress anchoring
    op.add_column('enrollments', sa.Column('course_version', sa.Integer(), nullable=True, server_default='1'))

    # Create slug index separately (unique index)
    op.create_index('idx_course_slug', 'courses', ['slug'], unique=True)


def downgrade() -> None:
    op.drop_index('idx_course_slug', table_name='courses')

    with op.batch_alter_table('enrollments') as batch_op:
        batch_op.drop_column('course_version')

    # batch_alter_table required for SQLite DROP COLUMN
    with op.batch_alter_table('courses') as batch_op:
        for col in [
            'slug', 'summary', 'thumbnail_url', 'audience_level', 'learning_objectives',
            'category', 'tags', 'estimated_duration_minutes', 'ai_tone_preset',
            'ai_custom_prompt', 'navigation_mode', 'default_pass_rate',
            'default_quiz_attempts', 'default_quiz_time_limit_seconds',
            'certificate_enabled', 'published_at', 'version',
        ]:
            batch_op.drop_column(col)
    # Note: PostgreSQL enum values cannot be removed — downgrade leaves has_unpublished_changes value
