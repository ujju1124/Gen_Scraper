"""
Categories API router.
Provides endpoints for fetching categories and their associated sources.
"""
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from dependencies import get_db
from models.category import Category
from models.source import Source

router = APIRouter()

@router.get("/")
def get_categories(db: Session = Depends(get_db)):
    """
    Get all categories.
    
    Returns list of all categories with id, name, and display_name.
    """
    categories = db.query(Category).all()
    return {
        "items": [
            {
                "id": cat.id,
                "name": cat.name,
                "display_name": cat.display_name
            }
            for cat in categories
        ]
    }

@router.get("/{category_id}/sources")
def get_sources_for_category(category_id: int, db: Session = Depends(get_db)):
    """
    Get all active sources for a given category.
    
    Returns list of sources with id, name, and display_name.
    """
    sources = db.query(Source).filter(
        Source.category_id == category_id,
        Source.is_active == True
    ).all()
    
    return [
        {
            "id": s.id,
            "name": s.name,
            "display_name": s.display_name
        }
        for s in sources
    ]