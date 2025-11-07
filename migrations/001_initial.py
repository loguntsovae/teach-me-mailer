"""Initial database schema with UUIDs and hashed API keys

Revision ID: 001_initial_v3
Revises: 
Create Date: 2024-11-07 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_initial_v3'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create api_keys table
    op.create_table(
        'api_keys',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('key_hash', sa.Text(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('daily_limit', sa.Integer(), nullable=False, server_default=sa.text('15')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    
    # Create unique index on key_hash
    op.create_index('ix_api_keys_key_hash', 'api_keys', ['key_hash'], unique=True)
    op.create_index('ix_api_keys_is_active', 'api_keys', ['is_active'])
    
    # Create send_logs table
    op.create_table(
        'send_logs',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('api_key_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('api_keys.id'), nullable=False),
        sa.Column('sent_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('recipient', sa.String(255), nullable=False),
        sa.Column('message_id', sa.Text(), nullable=True),
    )
    
    # Create indexes on send_logs
    op.create_index('ix_send_logs_api_key_id', 'send_logs', ['api_key_id'])
    op.create_index('ix_send_logs_sent_at', 'send_logs', ['sent_at'])
    
    # Create daily_usage table
    op.create_table(
        'daily_usage',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('api_key_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('api_keys.id'), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('count', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    
    # Create indexes on daily_usage
    op.create_index('ix_daily_usage_api_key_id', 'daily_usage', ['api_key_id'])
    op.create_index('ix_daily_usage_date', 'daily_usage', ['date'])
    
    # Create unique constraint on api_key_id + date (critical for atomic upserts)
    op.create_unique_constraint('uq_daily_usage_api_key_date', 'daily_usage', ['api_key_id', 'date'])


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('daily_usage')
    op.drop_table('send_logs') 
    op.drop_table('api_keys')