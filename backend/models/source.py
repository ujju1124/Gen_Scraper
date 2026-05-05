from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from database import Base


class Source(Base):
    __tablename__ = "sources"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    name = Column(String(100), nullable=False)  # e.g. "booking_com"
    display_name = Column(String(100), nullable=False)  # e.g. "Booking.com"
    base_url = Column(String(300), nullable=False)
    heal_mode = Column(String(20), nullable=False, default="AUTO")  # 'AUTO' or 'MANUAL'
    field_hints = Column(JSONB, nullable=True)  # real example values per field
    is_active = Column(Boolean, nullable=False, default=True)
    consecutive_failure_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
