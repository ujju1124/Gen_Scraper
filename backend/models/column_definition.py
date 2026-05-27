"""
Column Definition Model

Stores custom column definitions for the admin panel.
Replaces localStorage-based column storage with database persistence.
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from database import Base


class ColumnDefinition(Base):
    """
    Custom column definitions for admin panel.
    
    Attributes:
        id: Primary key
        name: Column key (e.g., "custom_verification_status")
        display_name: Human-readable label (e.g., "Verification Status")
        is_temporary: If True, column is session-scoped (cleared on refresh)
        created_by: User ID who created this column
        created_at: Timestamp when column was created
        updated_at: Timestamp when column was last updated
    """
    __tablename__ = "column_definitions"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True, index=True)
    display_name = Column(String(200), nullable=False)
    is_temporary = Column(Boolean, default=False, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationship to user
    creator = relationship("User", foreign_keys=[created_by])
    
    def __repr__(self):
        return f"<ColumnDefinition(id={self.id}, name={self.name}, display_name={self.display_name})>"
