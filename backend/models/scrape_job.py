from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, ARRAY, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func, text
from database import Base


class ScrapeJob(Base):
    __tablename__ = "scrape_jobs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    location = Column(String(200), nullable=False)
    source_ids = Column(ARRAY(Integer), nullable=True)
    failed_source_ids = Column(ARRAY(Integer), nullable=True)
    parent_job_id = Column(UUID(as_uuid=True), ForeignKey("scrape_jobs.id"), nullable=True)
    max_results = Column(Integer, nullable=True)  # None = scrape all (max), integer = limit per source
    status = Column(String(20), nullable=False, default="QUEUED", index=True)
    error_message = Column(Text, nullable=True)
    celery_task_id = Column(String(200), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Go scraper settings — stored per job for Google Maps source
    # e.g. {"geo_coordinates": "27.693444,85.281924", "zoom": 14, "max_depth": 20, "radius": 5}
    google_maps_settings = Column(JSONB, nullable=True)
    
    # Job statistics — stored after job completion
    # e.g. {"raw_scraped": 95, "new_records": 10, "duplicates": 85, "by_source": {1: 75, 32: 20}}
    statistics = Column(JSONB, nullable=True)
    
    # Scraping progress — updated during job execution for live progress display
    # e.g. "🔍 Searching Google Maps...", "✅ Google Maps complete - 30 hotels found"
    scraping_progress = Column(String, nullable=True)

    # Phase 1 — skip existing records option
    skip_existing = Column(Boolean, nullable=True, default=False)
