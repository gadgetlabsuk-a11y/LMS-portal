"""Create course_source_documents table for AI content generation.

Revision ID: 007
Revises: 006
Create Date: 2026-05-22
"""
from alembic import op
import sqlalchemy as sa

revision = '007'
down_revision = '006'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'course_source_documents',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('course_id', sa.Integer(), sa.ForeignKey('courses.id', ondelete='CASCADE'), nullable=False),
        sa.Column('filename', sa.String(length=500), nullable=False),
        sa.Column('content_type', sa.String(length=200), nullable=True),
        sa.Column('char_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('extracted_text', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_source_doc_course', 'course_source_documents', ['course_id'])


def downgrade() -> None:
    op.drop_index('idx_source_doc_course', table_name='course_source_documents')
    op.drop_table('course_source_documents')
