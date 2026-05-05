from sqlalchemy import Column, Integer, String, DateTime, Numeric
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from database import Base


class GeocodingCache(Base):
    __tablename__ = "geocoding_cache"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    location_name = Column(String(200), nullable=False, unique=True)
    address = Column(String(500), nullable=True)
    city = Column(String(100), nullable=True)
    country = Column(String(100), nullable=True, default="Nepal")
    latitude = Column(Numeric(10, 7), nullable=True)
    longitude = Column(Numeric(10, 7), nullable=True)
    source = Column(String(50), nullable=True, default="overpass")
    confidence = Column(Numeric(3, 2), nullable=True, default=1.0)
    bounding_box = Column(JSONB, nullable=True)
    cached_at = Column(DateTime(timezone=True), server_default=func.now())
