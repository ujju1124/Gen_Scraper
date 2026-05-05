"""Add address, city, country, source, confidence columns to geocoding_cache

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-29 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade():
    # Add new columns to geocoding_cache
    op.add_column('geocoding_cache', sa.Column('address', sa.String(length=500), nullable=True))
    op.add_column('geocoding_cache', sa.Column('city', sa.String(length=100), nullable=True))
    op.add_column('geocoding_cache', sa.Column('country', sa.String(length=100), nullable=True, server_default='Nepal'))
    op.add_column('geocoding_cache', sa.Column('source', sa.String(length=50), nullable=True, server_default='overpass'))
    op.add_column('geocoding_cache', sa.Column('confidence', sa.Numeric(precision=3, scale=2), nullable=True, server_default='1.0'))


def downgrade():
    # Remove columns
    op.drop_column('geocoding_cache', 'confidence')
    op.drop_column('geocoding_cache', 'source')
    op.drop_column('geocoding_cache', 'country')
    op.drop_column('geocoding_cache', 'city')
    op.drop_column('geocoding_cache', 'address')
