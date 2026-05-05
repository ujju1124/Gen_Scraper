from sqlalchemy import Column, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func, text
from database import Base


class RawResult(Base):
    __tablename__ = "raw_results"
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    job_id = Column(UUID(as_uuid=True), ForeignKey("scrape_jobs.id"), nullable=False, index=True)
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=False, index=True)
    raw_data = Column(JSONB, nullable=False)
    scraped_at = Column(DateTime(timezone=True), server_default=func.now())
