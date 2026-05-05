from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, ARRAY
from sqlalchemy.dialects.postgresql import UUID
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
