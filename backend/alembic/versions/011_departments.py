"""Add departments, department_members, department_content tables.

Departments group users; courses/podcasts are assigned to a department and optionally
marked mandatory with a deadline. See docs/superpowers/specs/2026-05-23-departments-design.md.

Revision ID: 011
Revises: 010
Create Date: 2026-05-23
"""
from alembic import op
import sqlalchemy as sa

revision = '011'
down_revision = '010'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'departments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', name='uq_department_name'),
    )

    op.create_table(
        'department_members',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('department_id', sa.Integer(), sa.ForeignKey('departments.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('added_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('department_id', 'user_id', name='uq_department_user'),
    )
    op.create_index('idx_department_member_user', 'department_members', ['user_id'])
    op.create_index('idx_department_member_dept', 'department_members', ['department_id'])

    op.create_table(
        'department_content',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('department_id', sa.Integer(), sa.ForeignKey('departments.id', ondelete='CASCADE'), nullable=False),
        sa.Column('course_id', sa.Integer(), sa.ForeignKey('courses.id', ondelete='CASCADE'), nullable=True),
        sa.Column('broadcast_id', sa.Integer(), sa.ForeignKey('broadcasts.id', ondelete='CASCADE'), nullable=True),
        sa.Column('mandatory', sa.Boolean(), server_default='0', nullable=False),
        sa.Column('due_mode', sa.String(length=20), nullable=True),
        sa.Column('due_date', sa.DateTime(), nullable=True),
        sa.Column('due_days', sa.Integer(), nullable=True),
        sa.Column('assigned_by', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('department_id', 'course_id', name='uq_department_course'),
        sa.UniqueConstraint('department_id', 'broadcast_id', name='uq_department_broadcast'),
    )
    op.create_index('idx_department_content_course', 'department_content', ['course_id'])
    op.create_index('idx_department_content_broadcast', 'department_content', ['broadcast_id'])


def downgrade() -> None:
    op.drop_index('idx_department_content_broadcast', table_name='department_content')
    op.drop_index('idx_department_content_course', table_name='department_content')
    op.drop_table('department_content')
    op.drop_index('idx_department_member_dept', table_name='department_members')
    op.drop_index('idx_department_member_user', table_name='department_members')
    op.drop_table('department_members')
    op.drop_table('departments')
