from sqlalchemy import Column, Integer, String, Numeric
from database import Base


class CityBoundingBox(Base):
    __tablename__ = "city_bounding_boxes"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    city_name = Column(String(100), nullable=False, unique=True)
    min_lat = Column(Numeric(10, 7), nullable=True)
    min_lon = Column(Numeric(10, 7), nullable=True)
    max_lat = Column(Numeric(10, 7), nullable=True)
    max_lon = Column(Numeric(10, 7), nullable=True)
