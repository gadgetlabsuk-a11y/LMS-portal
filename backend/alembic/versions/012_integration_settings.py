"""Add integration_settings (single-row store for third-party API keys).

Set via the admin Settings page; a non-empty value overrides the matching env var
at runtime. See services/integration_settings_service.py.

Revision ID: 012
Revises: 011
Create Date: 2026-05-25
"""
from alembic import op
import sqlalchemy as sa

revision = '012'
down_revision = '011'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'integration_settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('elevenlabs_api_key', sa.String(length=255), nullable=True),
        sa.Column('deepgram_api_key', sa.String(length=255), nullable=True),
        sa.Column('claude_api_key', sa.String(length=255), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('updated_by', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('integration_settings')
