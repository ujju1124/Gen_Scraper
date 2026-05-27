"""add column_definitions table for custom columns

Revision ID: 0011
Revises: 0010
Create Date: 2026-05-25 19:40:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0011'
down_revision = '0010'
branch_labels = None
depends_on = None


def upgrade():
    """
    Add column_definitions table to store custom column definitions.
    
    This moves custom column definitions from browser localStorage to database:
    - Persistent across browsers and devices
    - Shared across all admin users
    - Supports temporary vs permanent columns
    """
    op.create_table('column_definitions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False, unique=True),
        sa.Column('display_name', sa.String(200), nullable=False),
        sa.Column('is_temporary', sa.Boolean(), default=False, nullable=False),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False)
    )
    
    # Create index on name for faster lookups
    op.create_index('ix_column_definitions_name', 'column_definitions', ['name'])


def downgrade():
    """Remove column_definitions table."""
    op.drop_index('ix_column_definitions_name', 'column_definitions')
    op.drop_table('column_definitions')
