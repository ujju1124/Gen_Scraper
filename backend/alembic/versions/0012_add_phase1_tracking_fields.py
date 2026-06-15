"""add phase1 tracking fields

Revision ID: 0012
Revises: 0011
Create Date: 2026-06-15

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '0012'
down_revision = '0011'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add tracking fields to cleaned_results
    op.add_column(
        'cleaned_results',
        sa.Column('is_new_record', sa.Boolean(), nullable=True, default=True)
    )
    op.add_column(
        'cleaned_results',
        sa.Column('is_updated_record', sa.Boolean(), nullable=True, default=False)
    )
    
    # Add skip_existing field to scrape_jobs
    op.add_column(
        'scrape_jobs',
        sa.Column('skip_existing', sa.Boolean(), nullable=True, default=False)
    )


def downgrade() -> None:
    op.drop_column('cleaned_results', 'is_updated_record')
    op.drop_column('cleaned_results', 'is_new_record')
    op.drop_column('scrape_jobs', 'skip_existing')
