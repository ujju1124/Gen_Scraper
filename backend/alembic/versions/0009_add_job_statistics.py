"""add job statistics

Revision ID: 0009
Revises: 0008
Create Date: 2026-05-25

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0009'
down_revision = '0008'
branch_labels = None
depends_on = None


def upgrade():
    # Add statistics JSONB column to scrape_jobs table
    op.add_column('scrape_jobs', sa.Column('statistics', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade():
    # Remove statistics column
    op.drop_column('scrape_jobs', 'statistics')
