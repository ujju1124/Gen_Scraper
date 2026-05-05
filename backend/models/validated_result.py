from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func, text
from database import Base


class ValidatedResult(Base):
    __tablename__ = "validated_results"
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    cleaned_result_id = Column(UUID(as_uuid=True), ForeignKey("cleaned_results.id"), nullable=False, unique=True)
    job_id = Column(UUID(as_uuid=True), ForeignKey("scrape_jobs.id"), nullable=True, index=True)
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True, index=True)
    validated_by = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    validated_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    notes = Column(Text, nullable=True)
