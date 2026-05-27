"""add user_overrides column for temporary edits

Revision ID: 0008
Revises: 0007
Create Date: 2026-05-25 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0008'
down_revision = '0007'
branch_labels = None
depends_on = None


def upgrade():
    """
    Add user_overrides JSONB column to cleaned_results table.
    
    This column stores temporary field changes separately from permanent ones:
    {
      "phone_primary": {"value": "new-phone", "temp": true, "edited_by": 1, "edited_at": "2026-05-25T13:00:00"},
      "name": {"value": "New Name", "temp": false, "edited_by": 1, "edited_at": "2026-05-25T13:05:00"}
    }
    """
    op.add_column('cleaned_results',
        sa.Column('user_overrides', postgresql.JSONB, nullable=True)
    )


def downgrade():
    """Remove user_overrides column."""
    op.drop_column('cleaned_results', 'user_overrides')
