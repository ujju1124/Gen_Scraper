"""add scraping progress field

Revision ID: 0010
Revises: 0009
Create Date: 2026-05-25 17:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0010'
down_revision = '0009'
branch_labels = None
depends_on = None


def upgrade():
    # Add scraping_progress column to scrape_jobs table
    op.add_column('scrape_jobs', sa.Column('scraping_progress', sa.String(), nullable=True))


def downgrade():
    # Remove scraping_progress column
    op.drop_column('scrape_jobs', 'scraping_progress')
