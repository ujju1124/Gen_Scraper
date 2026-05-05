"""
Admin Sources routes.
Handles admin-only operations for managing sources (enable/disable).
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict, Field

from dependencies import get_db, require_admin
from models import User, Source, Category

router = APIRouter()


# Request/Response schemas
class UpdateSourceRequest(BaseModel):
    is_active: bool = Field(..., description="Whether the source is active")


class SourceResponse(BaseModel):
    id: int
    category_id: int
    name: str
    display_name: str
    base_url: str
    is_active: bool
    created_at: str
    
    model_config = ConfigDict(from_attributes=True)


class SourceWithCategoryResponse(BaseModel):
    id: int
    category_id: int
    category_name: str
    name: str
    display_name: str
    base_url: str
    is_active: bool
    created_at: str


@router.get("/sources", response_model=List[SourceWithCategoryResponse])
def get_all_sources(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Get all sources with their category information.
    
    - Protected by require_admin dependency
    - Returns all sources with is_active status
    - Includes category name for display
    """
    # Query all sources with category join
    sources = db.query(Source, Category).join(
        Category, Source.category_id == Category.id
    ).all()
    
    # Convert to response format
    result = []
    for source, category in sources:
        result.append({
            "id": source.id,
            "category_id": source.category_id,
            "category_name": category.display_name,
            "name": source.name,
            "display_name": source.display_name,
            "base_url": source.base_url,
            "is_active": source.is_active,
            "created_at": source.created_at.isoformat() if source.created_at else None
        })
    
    return result


@router.patch("/sources/{source_id}", response_model=SourceResponse)
def update_source(
    source_id: int,
    update_request: UpdateSourceRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Update source is_active status.
    
    - Protected by require_admin dependency
    - Only updates is_active field
    - Returns 404 if source not found
    """
    # Find source
    source = db.query(Source).filter(Source.id == source_id).first()
    
    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source not found"
        )
    
    # Update is_active field
    source.is_active = update_request.is_active
    db.commit()
    db.refresh(source)
    
    return {
        "id": source.id,
        "category_id": source.category_id,
        "name": source.name,
        "display_name": source.display_name,
        "base_url": source.base_url,
        "is_active": source.is_active,
        "created_at": source.created_at.isoformat() if source.created_at else None
    }
