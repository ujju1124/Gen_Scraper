"""add extra_data to cleaned_results and google_maps_settings to scrape_jobs

Revision ID: 0007
Revises: 0006
Create Date: 2026-05-20 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision = '0007'
down_revision = '0006'
branch_labels = None
depends_on = None


def upgrade():
    # Add extra_data column to cleaned_results (stores Go scraper's 33+ rich fields)
    op.add_column(
        'cleaned_results',
        sa.Column('extra_data', JSONB, nullable=True)
    )
    op.create_index(
        'idx_cleaned_results_extra_data',
        'cleaned_results',
        ['extra_data'],
        postgresql_using='gin'
    )

    # Add google_maps_settings to scrape_jobs (stores Go scraper params)
    op.add_column(
        'scrape_jobs',
        sa.Column('google_maps_settings', JSONB, nullable=True)
    )

    # Add scraper_source to cleaned_results (tracks which scraper produced the result)
    op.add_column(
        'cleaned_results',
        sa.Column('scraper_source', sa.String(50), nullable=True)
    )


def downgrade():
    op.drop_column('cleaned_results', 'scraper_source')
    op.drop_index('idx_cleaned_results_extra_data', table_name='cleaned_results')
    op.drop_column('cleaned_results', 'extra_data')
    op.drop_column('scrape_jobs', 'google_maps_settings')
