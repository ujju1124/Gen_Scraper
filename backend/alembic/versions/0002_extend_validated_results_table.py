"""Extend validated_results table for Phase 4A

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-28 14:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Get connection to check if columns exist
    conn = op.get_bind()
    
    # Check if old columns exist before renaming
    result = conn.execute(sa.text("""
        SELECT column_name FROM information_schema.columns 
        WHERE table_name='validated_results' AND column_name IN ('pushed_at', 'pushed_by')
    """))
    old_columns = [row[0] for row in result]
    
    # Rename columns only if they exist
    if 'pushed_at' in old_columns:
        op.alter_column('validated_results', 'pushed_at', new_column_name='validated_at')
    if 'pushed_by' in old_columns:
        op.alter_column('validated_results', 'pushed_by', new_column_name='validated_by')
    
    # Check if new columns already exist
    result = conn.execute(sa.text("""
        SELECT column_name FROM information_schema.columns 
        WHERE table_name='validated_results' AND column_name IN ('job_id', 'source_id', 'category_id')
    """))
    existing_columns = [row[0] for row in result]
    
    # Add new columns only if they don't exist
    if 'job_id' not in existing_columns:
        op.add_column('validated_results', sa.Column('job_id', postgresql.UUID(as_uuid=True), nullable=True))
    if 'source_id' not in existing_columns:
        op.add_column('validated_results', sa.Column('source_id', sa.Integer(), nullable=True))
    if 'category_id' not in existing_columns:
        op.add_column('validated_results', sa.Column('category_id', sa.Integer(), nullable=True))
    
    # Check if foreign keys already exist
    result = conn.execute(sa.text("""
        SELECT constraint_name FROM information_schema.table_constraints 
        WHERE table_name='validated_results' AND constraint_type='FOREIGN KEY'
        AND constraint_name IN ('fk_validated_results_job_id', 'fk_validated_results_source_id', 'fk_validated_results_category_id')
    """))
    existing_fks = [row[0] for row in result]
    
    # Add foreign key constraints only if they don't exist
    if 'fk_validated_results_job_id' not in existing_fks:
        op.create_foreign_key('fk_validated_results_job_id', 'validated_results', 'scrape_jobs', ['job_id'], ['id'])
    if 'fk_validated_results_source_id' not in existing_fks:
        op.create_foreign_key('fk_validated_results_source_id', 'validated_results', 'sources', ['source_id'], ['id'])
    if 'fk_validated_results_category_id' not in existing_fks:
        op.create_foreign_key('fk_validated_results_category_id', 'validated_results', 'categories', ['category_id'], ['id'])
    
    # Check if indexes already exist
    result = conn.execute(sa.text("""
        SELECT indexname FROM pg_indexes 
        WHERE tablename='validated_results' 
        AND indexname IN ('idx_validated_results_job_id', 'idx_validated_results_category_id', 
                          'idx_validated_results_validated_at', 'idx_validated_results_validated_by')
    """))
    existing_indexes = [row[0] for row in result]
    
    # Create indexes only if they don't exist
    if 'idx_validated_results_job_id' not in existing_indexes:
        op.create_index('idx_validated_results_job_id', 'validated_results', ['job_id'])
    if 'idx_validated_results_category_id' not in existing_indexes:
        op.create_index('idx_validated_results_category_id', 'validated_results', ['category_id'])
    if 'idx_validated_results_validated_at' not in existing_indexes:
        op.create_index('idx_validated_results_validated_at', 'validated_results', ['validated_at'])
    if 'idx_validated_results_validated_by' not in existing_indexes:
        op.create_index('idx_validated_results_validated_by', 'validated_results', ['validated_by'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_validated_results_validated_by', table_name='validated_results')
    op.drop_index('idx_validated_results_validated_at', table_name='validated_results')
    op.drop_index('idx_validated_results_category_id', table_name='validated_results')
    op.drop_index('idx_validated_results_job_id', table_name='validated_results')
    
    # Drop foreign key constraints
    op.drop_constraint('fk_validated_results_category_id', 'validated_results', type_='foreignkey')
    op.drop_constraint('fk_validated_results_source_id', 'validated_results', type_='foreignkey')
    op.drop_constraint('fk_validated_results_job_id', 'validated_results', type_='foreignkey')
    
    # Drop new columns
    op.drop_column('validated_results', 'category_id')
    op.drop_column('validated_results', 'source_id')
    op.drop_column('validated_results', 'job_id')
    
    # Rename columns back
    op.alter_column('validated_results', 'validated_by', new_column_name='pushed_by')
    op.alter_column('validated_results', 'validated_at', new_column_name='pushed_at')
