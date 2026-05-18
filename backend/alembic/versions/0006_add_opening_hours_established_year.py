"""add opening_hours and established_year fields

Revision ID: 0006
Revises: 0005
Create Date: 2026-05-15 04:20:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0006'
down_revision = '0005'
branch_labels = None
depends_on = None


def upgrade():
    # Add opening_hours column
    op.add_column('cleaned_results', sa.Column('opening_hours', sa.Text(), nullable=True))
    
    # Add established_year column
    op.add_column('cleaned_results', sa.Column('established_year', sa.Integer(), nullable=True))


def downgrade():
    # Remove columns
    op.drop_column('cleaned_results', 'established_year')
    op.drop_column('cleaned_results', 'opening_hours')
