"""add merge columns to cleaned_results

Revision ID: 0005
Revises: 0004
Create Date: 2026-05-03

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '0005'
down_revision = '0004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'cleaned_results',
        sa.Column('merged_from_sources', postgresql.ARRAY(sa.Integer()), nullable=True)
    )
    op.add_column(
        'cleaned_results',
        sa.Column('confidence_score', sa.Numeric(3, 2), nullable=True)
    )
    op.add_column(
        'cleaned_results',
        sa.Column('merged_at', sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('cleaned_results', 'merged_at')
    op.drop_column('cleaned_results', 'confidence_score')
    op.drop_column('cleaned_results', 'merged_from_sources')
