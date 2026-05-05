"""Initial schema with all 12 tables and indexes

Revision ID: 0001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable UUID extension
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    
    # Table 1: users (no dependencies)
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('email', sa.String(length=200), nullable=False),
        sa.Column('password_hash', sa.String(length=300), nullable=False),
        sa.Column('role', sa.String(length=20), nullable=False, server_default='user'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    op.create_index('ix_users_email', 'users', ['email'])
    
    # Table 2: refresh_tokens (depends on users)
    op.create_table(
        'refresh_tokens',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('revoked', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token_hash')
    )
    op.create_index('idx_refresh_tokens_user_id', 'refresh_tokens', ['user_id'])
    op.create_index('idx_refresh_tokens_token_hash', 'refresh_tokens', ['token_hash'])
    
    # Table 3: categories (no dependencies)
    op.create_table(
        'categories',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('display_name', sa.String(length=100), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    
    # Table 4: sources (depends on categories)
    op.create_table(
        'sources',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('category_id', sa.Integer(), nullable=True),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('display_name', sa.String(length=100), nullable=False),
        sa.Column('base_url', sa.String(length=300), nullable=False),
        sa.Column('heal_mode', sa.String(length=20), nullable=False, server_default='AUTO'),
        sa.Column('field_hints', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('consecutive_failure_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['category_id'], ['categories.id']),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Table 5: scrape_jobs (depends on users, categories)
    op.create_table(
        'scrape_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('category_id', sa.Integer(), nullable=False),
        sa.Column('location', sa.String(length=200), nullable=False),
        sa.Column('source_ids', postgresql.ARRAY(sa.Integer()), nullable=True),
        sa.Column('failed_source_ids', postgresql.ARRAY(sa.Integer()), nullable=True),
        sa.Column('parent_job_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='QUEUED'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('celery_task_id', sa.String(length=200), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['category_id'], ['categories.id']),
        sa.ForeignKeyConstraint(['parent_job_id'], ['scrape_jobs.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_scrape_jobs_status', 'scrape_jobs', ['status'])
    op.create_index('idx_scrape_jobs_user_id', 'scrape_jobs', ['user_id'])
    op.create_index('idx_scrape_jobs_created_at', 'scrape_jobs', [sa.text('created_at DESC')])
    
    # Table 6: raw_results (depends on scrape_jobs, sources)
    op.create_table(
        'raw_results',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('job_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('source_id', sa.Integer(), nullable=False),
        sa.Column('raw_data', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('scraped_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['job_id'], ['scrape_jobs.id']),
        sa.ForeignKeyConstraint(['source_id'], ['sources.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_raw_results_job_id', 'raw_results', ['job_id'])
    op.create_index('idx_raw_results_source_id', 'raw_results', ['source_id'])
    
    # Table 7: cleaned_results (depends on scrape_jobs, sources, categories)
    op.create_table(
        'cleaned_results',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('job_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('source_id', sa.Integer(), nullable=False),
        sa.Column('category_id', sa.Integer(), nullable=False),
        sa.Column('dedup_key', sa.String(length=64), nullable=True),
        # Identity
        sa.Column('name', sa.String(length=300), nullable=True),
        sa.Column('brand', sa.String(length=200), nullable=True),
        sa.Column('property_type', sa.String(length=100), nullable=True),
        sa.Column('star_rating', sa.SmallInteger(), nullable=True),
        # Location
        sa.Column('address', sa.Text(), nullable=True),
        sa.Column('street_address', sa.String(length=300), nullable=True),
        sa.Column('city', sa.String(length=100), nullable=True),
        sa.Column('district', sa.String(length=100), nullable=True),
        sa.Column('province', sa.String(length=100), nullable=True),
        sa.Column('country', sa.String(length=100), nullable=True, server_default='Nepal'),
        sa.Column('latitude', sa.Numeric(precision=10, scale=7), nullable=True),
        sa.Column('longitude', sa.Numeric(precision=10, scale=7), nullable=True),
        sa.Column('neighbourhood', sa.String(length=200), nullable=True),
        sa.Column('nearby_landmark', sa.String(length=300), nullable=True),
        # Contact
        sa.Column('phone_primary', sa.String(length=50), nullable=True),
        sa.Column('phone_secondary', sa.String(length=50), nullable=True),
        sa.Column('email', sa.String(length=200), nullable=True),
        sa.Column('website', sa.String(length=500), nullable=True),
        sa.Column('facebook_url', sa.String(length=500), nullable=True),
        sa.Column('instagram_handle', sa.String(length=200), nullable=True),
        sa.Column('whatsapp_number', sa.String(length=50), nullable=True),
        # Pricing
        sa.Column('price_min', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('price_max', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('currency', sa.String(length=10), nullable=True, server_default='NPR'),
        sa.Column('price_range_label', sa.String(length=20), nullable=True),
        sa.Column('includes_breakfast', sa.Boolean(), nullable=True),
        sa.Column('includes_taxes', sa.Boolean(), nullable=True),
        # Reviews
        sa.Column('rating_overall', sa.Numeric(precision=4, scale=2), nullable=True),
        sa.Column('rating_label', sa.String(length=50), nullable=True),
        sa.Column('review_count', sa.Integer(), nullable=True),
        sa.Column('rating_cleanliness', sa.Numeric(precision=4, scale=2), nullable=True),
        sa.Column('rating_location', sa.Numeric(precision=4, scale=2), nullable=True),
        sa.Column('rating_facilities', sa.Numeric(precision=4, scale=2), nullable=True),
        sa.Column('rating_service', sa.Numeric(precision=4, scale=2), nullable=True),
        sa.Column('rating_value', sa.Numeric(precision=4, scale=2), nullable=True),
        # Facilities
        sa.Column('amenities', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('pets_allowed', sa.Boolean(), nullable=True),
        sa.Column('breakfast_available', sa.Boolean(), nullable=True),
        sa.Column('checkin_time', sa.String(length=20), nullable=True),
        sa.Column('checkout_time', sa.String(length=20), nullable=True),
        sa.Column('cancellation_policy', sa.Text(), nullable=True),
        sa.Column('free_cancellation', sa.Boolean(), nullable=True),
        # Media
        sa.Column('thumbnail_url', sa.Text(), nullable=True),
        sa.Column('image_urls', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('image_count', sa.Integer(), nullable=True),
        # Content
        sa.Column('description_short', sa.Text(), nullable=True),
        sa.Column('description_full', sa.Text(), nullable=True),
        sa.Column('highlights', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('popular_with', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('staff_languages', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        # Metadata
        sa.Column('source_url', sa.Text(), nullable=True),
        sa.Column('source_listing_id', sa.String(length=200), nullable=True),
        sa.Column('data_completeness', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('is_edited', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_duplicate', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='PENDING'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['job_id'], ['scrape_jobs.id']),
        sa.ForeignKeyConstraint(['source_id'], ['sources.id']),
        sa.ForeignKeyConstraint(['category_id'], ['categories.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_cleaned_results_job_id', 'cleaned_results', ['job_id'])
    op.create_index('idx_cleaned_results_status', 'cleaned_results', ['status'])
    op.create_index('idx_cleaned_results_category_id', 'cleaned_results', ['category_id'])
    op.create_index('idx_cleaned_results_data_complete', 'cleaned_results', [sa.text('data_completeness DESC')])
    op.create_index('idx_cleaned_results_dedup_key', 'cleaned_results', ['dedup_key'])
    op.create_index('idx_cleaned_results_city', 'cleaned_results', ['city'])
    
    # Table 8: validated_results (depends on cleaned_results, users)
    op.create_table(
        'validated_results',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('cleaned_result_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('pushed_by', sa.Integer(), nullable=True),
        sa.Column('pushed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['cleaned_result_id'], ['cleaned_results.id']),
        sa.ForeignKeyConstraint(['pushed_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('cleaned_result_id')
    )
    
    # Table 9: scraper_selectors (depends on sources)
    op.create_table(
        'scraper_selectors',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('source_id', sa.Integer(), nullable=False),
        sa.Column('field_name', sa.String(length=100), nullable=False),
        sa.Column('selector', sa.Text(), nullable=False),
        sa.Column('selector_type', sa.String(length=30), nullable=False),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('html_snapshot_hash', sa.String(length=64), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.ForeignKeyConstraint(['source_id'], ['sources.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('source_id', 'field_name', name='uq_source_field')
    )
    
    # Table 10: selector_heal_log (depends on sources, users)
    op.create_table(
        'selector_heal_log',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('source_id', sa.Integer(), nullable=False),
        sa.Column('field_name', sa.String(length=100), nullable=True),
        sa.Column('old_selector', sa.Text(), nullable=True),
        sa.Column('new_selector', sa.Text(), nullable=True),
        sa.Column('trigger', sa.String(length=30), nullable=True),
        sa.Column('confidence', sa.Numeric(precision=4, scale=2), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='PENDING'),
        sa.Column('html_snapshot', sa.Text(), nullable=True),
        sa.Column('resolved_by', sa.Integer(), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('healed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['source_id'], ['sources.id']),
        sa.ForeignKeyConstraint(['resolved_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_heal_log_source_id', 'selector_heal_log', ['source_id'])
    op.create_index('idx_heal_log_status', 'selector_heal_log', ['status'])
    
    # Table 11: geocoding_cache (no dependencies)
    op.create_table(
        'geocoding_cache',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('location_name', sa.String(length=200), nullable=False),
        sa.Column('latitude', sa.Numeric(precision=10, scale=7), nullable=True),
        sa.Column('longitude', sa.Numeric(precision=10, scale=7), nullable=True),
        sa.Column('bounding_box', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('cached_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('location_name')
    )
    
    # Table 12: city_bounding_boxes (no dependencies)
    op.create_table(
        'city_bounding_boxes',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('city_name', sa.String(length=100), nullable=False),
        sa.Column('min_lat', sa.Numeric(precision=10, scale=7), nullable=True),
        sa.Column('min_lon', sa.Numeric(precision=10, scale=7), nullable=True),
        sa.Column('max_lat', sa.Numeric(precision=10, scale=7), nullable=True),
        sa.Column('max_lon', sa.Numeric(precision=10, scale=7), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('city_name')
    )


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('city_bounding_boxes')
    op.drop_table('geocoding_cache')
    op.drop_index('idx_heal_log_status', table_name='selector_heal_log')
    op.drop_index('idx_heal_log_source_id', table_name='selector_heal_log')
    op.drop_table('selector_heal_log')
    op.drop_table('scraper_selectors')
    op.drop_table('validated_results')
    op.drop_index('idx_cleaned_results_city', table_name='cleaned_results')
    op.drop_index('idx_cleaned_results_dedup_key', table_name='cleaned_results')
    op.drop_index('idx_cleaned_results_data_complete', table_name='cleaned_results')
    op.drop_index('idx_cleaned_results_category_id', table_name='cleaned_results')
    op.drop_index('idx_cleaned_results_status', table_name='cleaned_results')
    op.drop_index('idx_cleaned_results_job_id', table_name='cleaned_results')
    op.drop_table('cleaned_results')
    op.drop_index('idx_raw_results_source_id', table_name='raw_results')
    op.drop_index('idx_raw_results_job_id', table_name='raw_results')
    op.drop_table('raw_results')
    op.drop_index('idx_scrape_jobs_created_at', table_name='scrape_jobs')
    op.drop_index('idx_scrape_jobs_user_id', table_name='scrape_jobs')
    op.drop_index('idx_scrape_jobs_status', table_name='scrape_jobs')
    op.drop_table('scrape_jobs')
    op.drop_table('sources')
    op.drop_table('categories')
    op.drop_index('idx_refresh_tokens_token_hash', table_name='refresh_tokens')
    op.drop_index('idx_refresh_tokens_user_id', table_name='refresh_tokens')
    op.drop_table('refresh_tokens')
    op.drop_index('ix_users_email', table_name='users')
    op.drop_table('users')
    op.execute('DROP EXTENSION IF EXISTS "uuid-ossp"')
