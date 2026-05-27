from sqlalchemy import Column, Integer, String, SmallInteger, Text, Boolean, DateTime, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.sql import func, text
from database import Base


class CleanedResult(Base):
    __tablename__ = "cleaned_results"
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    job_id = Column(UUID(as_uuid=True), ForeignKey("scrape_jobs.id"), nullable=False, index=True)
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False, index=True)
    dedup_key = Column(String(64), nullable=True, index=True)
    
    # Identity
    name = Column(String(300), nullable=True)
    brand = Column(String(200), nullable=True)
    property_type = Column(String(100), nullable=True)
    star_rating = Column(SmallInteger, nullable=True)
    
    # Location
    address = Column(Text, nullable=True)
    street_address = Column(String(300), nullable=True)
    city = Column(String(100), nullable=True, index=True)
    district = Column(String(100), nullable=True)
    province = Column(String(100), nullable=True)
    country = Column(String(100), nullable=True, default="Nepal")
    latitude = Column(Numeric(10, 7), nullable=True)
    longitude = Column(Numeric(10, 7), nullable=True)
    neighbourhood = Column(String(200), nullable=True)
    nearby_landmark = Column(String(300), nullable=True)
    
    # Contact
    phone_primary = Column(String(50), nullable=True)
    phone_secondary = Column(String(50), nullable=True)
    email = Column(String(200), nullable=True)
    website = Column(String(500), nullable=True)
    facebook_url = Column(String(500), nullable=True)
    instagram_handle = Column(String(200), nullable=True)
    whatsapp_number = Column(String(50), nullable=True)
    
    # Pricing
    price_min = Column(Numeric(10, 2), nullable=True)
    price_max = Column(Numeric(10, 2), nullable=True)
    currency = Column(String(10), nullable=True, default="NPR")
    price_range_label = Column(String(20), nullable=True)
    includes_breakfast = Column(Boolean, nullable=True)
    includes_taxes = Column(Boolean, nullable=True)
    
    # Reviews
    rating_overall = Column(Numeric(4, 2), nullable=True)
    rating_label = Column(String(50), nullable=True)
    review_count = Column(Integer, nullable=True)
    rating_cleanliness = Column(Numeric(4, 2), nullable=True)
    rating_location = Column(Numeric(4, 2), nullable=True)
    rating_facilities = Column(Numeric(4, 2), nullable=True)
    rating_service = Column(Numeric(4, 2), nullable=True)
    rating_value = Column(Numeric(4, 2), nullable=True)
    
    # Facilities
    amenities = Column(JSONB, nullable=True)
    pets_allowed = Column(Boolean, nullable=True)
    breakfast_available = Column(Boolean, nullable=True)
    checkin_time = Column(String(20), nullable=True)
    checkout_time = Column(String(20), nullable=True)
    cancellation_policy = Column(Text, nullable=True)
    free_cancellation = Column(Boolean, nullable=True)
    
    # Media
    thumbnail_url = Column(Text, nullable=True)
    image_urls = Column(JSONB, nullable=True)
    image_count = Column(Integer, nullable=True)
    
    # Content
    description_short = Column(Text, nullable=True)
    description_full = Column(Text, nullable=True)
    highlights = Column(JSONB, nullable=True)
    popular_with = Column(JSONB, nullable=True)
    staff_languages = Column(JSONB, nullable=True)
    
    # Business Info
    opening_hours = Column(Text, nullable=True)
    established_year = Column(Integer, nullable=True)
    
    # Metadata
    source_url = Column(Text, nullable=True)
    source_listing_id = Column(String(200), nullable=True)
    data_completeness = Column(Numeric(5, 2), nullable=True, index=True)
    is_edited = Column(Boolean, nullable=False, default=False)
    is_duplicate = Column(Boolean, nullable=False, default=False)
    status = Column(String(20), nullable=False, default="PENDING", index=True)

    # Go scraper integration — tracks which scraper produced this result
    scraper_source = Column(String(50), nullable=True)  # 'go_scraper', 'serpapi', 'playwright'

    # Go scraper rich data — stores 33+ fields that don't fit standard columns
    # Includes: complete_address, user_reviews, images, open_hours, popular_times,
    #           place_id, data_id, cid, owner, about, reservations, order_online, menu
    extra_data = Column(JSONB, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Phase 6A — merge tracking
    merged_from_sources = Column(ARRAY(Integer), nullable=True)
    confidence_score    = Column(Numeric(3, 2), nullable=True)
    merged_at           = Column(DateTime(timezone=True), nullable=True)

    # Feature 2 — temporary field overrides
    # Stores temporary edits separately from permanent ones
    # Format: {"field_name": {"value": "new_value", "temp": true, "edited_by": 1, "edited_at": "2026-05-25T13:00:00"}}
    user_overrides = Column(JSONB, nullable=True)
