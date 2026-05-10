"""Create course_versions table for learner version pinning.

Revision ID: 005
Revises: 004
Create Date: 2026-05-10
"""
from alembic import op
import sqlalchemy as sa

revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'course_versions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('course_id', sa.Integer(), sa.ForeignKey('courses.id', ondelete='CASCADE'), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('snapshot', sa.JSON(), nullable=False),
        sa.Column('published_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('course_id', 'version_number', name='uq_course_version'),
    )
    op.create_index('idx_course_version', 'course_versions', ['course_id', 'version_number'])


def downgrade() -> None:
    op.drop_index('idx_course_version', table_name='course_versions')
    op.drop_table('course_versions')
