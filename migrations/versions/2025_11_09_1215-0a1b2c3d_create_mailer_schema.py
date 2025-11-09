"""create mailer schema

Revision ID: 0a1b2c3d4e5f
Revises: 
Create Date: 2025-11-09 12:15:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0a1b2c3d4e5f'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create the dedicated schema for application tables.
    op.execute("CREATE SCHEMA IF NOT EXISTS mailer")


def downgrade() -> None:
    # NOTE: CASCADE will drop all objects in the schema. Use with caution.
    op.execute("DROP SCHEMA IF EXISTS mailer CASCADE")
