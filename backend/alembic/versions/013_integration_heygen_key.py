"""Add integration_settings.heygen_api_key.

HeyGen avatar video (C-3) is still stubbed; the key is captured/stored now so it's
ready for when the integration is built. Not yet consumed by any service.

Revision ID: 013
Revises: 012
Create Date: 2026-05-25
"""
from alembic import op
import sqlalchemy as sa

revision = '013'
down_revision = '012'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('integration_settings') as batch_op:
        batch_op.add_column(sa.Column('heygen_api_key', sa.String(length=255), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('integration_settings') as batch_op:
        batch_op.drop_column('heygen_api_key')
