from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Numeric
from sqlalchemy.sql import func
from database import Base


class SelectorHealLog(Base):
    __tablename__ = "selector_heal_log"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=False, index=True)
    field_name = Column(String(100), nullable=True)
    old_selector = Column(Text, nullable=True)
    new_selector = Column(Text, nullable=True)
    trigger = Column(String(30), nullable=True)  # 'initial_load', 'auto_reheal', 'manual_fix'
    confidence = Column(Numeric(4, 2), nullable=True)  # 0.00–1.00
    status = Column(String(20), nullable=False, default="PENDING", index=True)
    html_snapshot = Column(Text, nullable=True)
    resolved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    healed_at = Column(DateTime(timezone=True), server_default=func.now())
