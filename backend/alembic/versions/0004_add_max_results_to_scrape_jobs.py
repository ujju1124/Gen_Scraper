"""add max_results to scrape_jobs

Revision ID: 0004
Revises: 0003
Create Date: 2026-04-29

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'scrape_jobs',
        sa.Column('max_results', sa.Integer(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('scrape_jobs', 'max_results')
