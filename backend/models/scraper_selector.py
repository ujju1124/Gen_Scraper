from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from database import Base


class ScraperSelector(Base):
    __tablename__ = "scraper_selectors"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=False)
    field_name = Column(String(100), nullable=False)
    selector = Column(Text, nullable=False)
    selector_type = Column(String(30), nullable=False)  # 'testid', 'css', 'xpath', 'role', 'json_ld'
    verified_at = Column(DateTime(timezone=True), nullable=True)
    html_snapshot_hash = Column(String(64), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    
    __table_args__ = (
        UniqueConstraint('source_id', 'field_name', name='uq_source_field'),
    )
