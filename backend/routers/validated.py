"""
Validated Results routes.
Public/client-facing API for accessing validated business data.
Now queries cleaned_results directly with status=APPROVED filter for live data.
"""
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict

from dependencies import get_db
from models import CleanedResult

router = APIRouter()


# Response schemas
class ValidatedResultResponse(BaseModel):
    """Response schema for a single validated result (approved cleaned_result)"""
    id: str
    job_id: str
    source_id: int
    source_name: Optional[str] = None
    category_id: int
    name: Optional[str]
    city: Optional[str]
    address: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    phone_primary: Optional[str]
    phone_secondary: Optional[str]
    email: Optional[str]
    website: Optional[str]
    description_short: Optional[str]
    rating_overall: Optional[float]
    review_count: Optional[int]
    price_min: Optional[float]
    price_max: Optional[float]
    currency: Optional[str]
    data_completeness: Optional[float]
    scraper_source: Optional[str] = None
    thumbnail_url: Optional[str] = None
    image_urls: Optional[list] = None
    amenities: Optional[list] = None
    opening_hours: Optional[str] = None
    # Rich fields from extra_data
    place_id: Optional[str] = None
    images_count: Optional[int] = None
    # User overrides (includes custom columns)
    user_overrides: Optional[dict] = None
    # Validation metadata
    validated_at: Optional[str] = None
    created_at: str
    
    model_config = ConfigDict(from_attributes=True)


class PaginatedValidatedResultsResponse(BaseModel):
    """Paginated response for validated results"""
    items: List[ValidatedResultResponse]
    total: int
    page: int
    page_size: int
    pages: int


@router.get("/", response_model=PaginatedValidatedResultsResponse)
def get_validated_results(
    category_id: Optional[int] = Query(None, description="Filter by category ID"),
    city: Optional[str] = Query(None, description="Filter by city name"),
    has_phone: Optional[bool] = Query(None, description="Filter by phone presence"),
    has_website: Optional[bool] = Query(None, description="Filter by website presence"),
    has_rating: Optional[bool] = Query(None, description="Filter by rating presence"),
    min_rating: Optional[float] = Query(None, ge=0, le=10, description="Minimum rating"),
    validated_after: Optional[str] = Query(None, description="Filter by validation date (ISO format: YYYY-MM-DD)"),
    validated_before: Optional[str] = Query(None, description="Filter by validation date (ISO format: YYYY-MM-DD)"),
    sort_by: str = Query("validated_at", description="Sort by field (validated_at or rating)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Page size (max 200)"),
    db: Session = Depends(get_db)
):
    """
    Get paginated validated results (approved cleaned_results with sent_to_validated=True).
    
    - Public endpoint (no authentication required) - can be used by client
    - Returns only validated, approved business data with live updates
    - Includes custom columns from user_overrides
    - Supports filtering by category, city, rating, etc.
    - Default page_size=50, max page_size=200
    """
    # Query cleaned_results with APPROVED status
    query = db.query(CleanedResult).filter(
        CleanedResult.status == "APPROVED"
    )
    
    # Apply filters
    if category_id:
        query = query.filter(CleanedResult.category_id == category_id)
    
    if city:
        query = query.filter(CleanedResult.city.ilike(f"%{city}%"))
    
    if has_phone is not None:
        if has_phone:
            query = query.filter(CleanedResult.phone_primary.isnot(None))
        else:
            query = query.filter(CleanedResult.phone_primary.is_(None))
    
    if has_website is not None:
        if has_website:
            query = query.filter(CleanedResult.website.isnot(None))
        else:
            query = query.filter(CleanedResult.website.is_(None))
    
    if has_rating is not None:
        if has_rating:
            query = query.filter(CleanedResult.rating_overall.isnot(None))
        else:
            query = query.filter(CleanedResult.rating_overall.is_(None))
    
    if min_rating is not None:
        query = query.filter(CleanedResult.rating_overall >= min_rating)
    
    if validated_after:
        try:
            date_after = datetime.fromisoformat(validated_after)
            query = query.filter(CleanedResult.updated_at >= date_after)
        except ValueError:
            pass
    
    if validated_before:
        try:
            date_before = datetime.fromisoformat(validated_before)
            query = query.filter(CleanedResult.updated_at <= date_before)
        except ValueError:
            pass
    
    # Apply sorting
    if sort_by == "rating":
        query = query.order_by(CleanedResult.rating_overall.desc().nullslast())
    else:  # default to updated_at (when it was last modified/approved)
        query = query.order_by(CleanedResult.updated_at.desc())
    
    # Get total count
    total = query.count()
    
    # Get paginated results
    results = query.offset((page - 1) * page_size).limit(page_size).all()
    
    # Calculate total pages
    pages = -(-total // page_size) if total > 0 else 0  # Ceiling division
    
    # Convert to response format
    items = []
    for cr in results:
        # Extract rich fields from extra_data
        place_id = cr.extra_data.get('place_id') if cr.extra_data else None
        images_count = len(cr.extra_data.get('images', [])) if cr.extra_data and cr.extra_data.get('images') else 0
        
        # Extract images
        images = []
        if cr.extra_data and cr.extra_data.get('images'):
            images = [img.get('link') for img in cr.extra_data['images'] if isinstance(img, dict) and img.get('link')]
        elif cr.image_urls:
            images = cr.image_urls
        
        items.append({
            "id": str(cr.id),
            "job_id": str(cr.job_id),
            "source_id": cr.source_id,
            "source_name": None,  # Can be joined if needed
            "category_id": cr.category_id,
            "name": cr.name,
            "city": cr.city,
            "address": cr.address,
            "latitude": float(cr.latitude) if cr.latitude else None,
            "longitude": float(cr.longitude) if cr.longitude else None,
            "phone_primary": cr.phone_primary,
            "phone_secondary": cr.phone_secondary,
            "email": cr.email,
            "website": cr.website,
            "description_short": cr.description_short,
            "rating_overall": float(cr.rating_overall) if cr.rating_overall else None,
            "review_count": cr.review_count,
            "price_min": float(cr.price_min) if cr.price_min else None,
            "price_max": float(cr.price_max) if cr.price_max else None,
            "currency": cr.currency,
            "data_completeness": float(cr.data_completeness) if cr.data_completeness else None,
            "scraper_source": cr.scraper_source,
            "thumbnail_url": cr.thumbnail_url,
            "image_urls": images,
            "amenities": cr.amenities if cr.amenities else [],
            "opening_hours": cr.opening_hours,
            "place_id": place_id,
            "images_count": images_count,
            "user_overrides": cr.user_overrides if cr.user_overrides else {},
            "validated_at": cr.updated_at.isoformat() if cr.updated_at else None,  # Use updated_at as validation time
            "created_at": cr.created_at.isoformat() if cr.created_at else None
        })
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": pages
    }


@router.get("/{result_id}", response_model=ValidatedResultResponse)
def get_validated_result_by_id(
    result_id: str,
    db: Session = Depends(get_db)
):
    """
    Get a single validated result by ID (cleaned_result ID).
    
    - Public endpoint (no authentication required)
    - Returns full business data for a specific validated result
    """
    # Find approved cleaned_result
    cr = db.query(CleanedResult).filter(
        CleanedResult.id == result_id,
        CleanedResult.status == "APPROVED"
    ).first()
    
    if not cr:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Validated result not found"
        )
    
    # Extract rich fields from extra_data
    place_id = cr.extra_data.get('place_id') if cr.extra_data else None
    images_count = len(cr.extra_data.get('images', [])) if cr.extra_data and cr.extra_data.get('images') else 0
    
    # Extract images
    images = []
    if cr.extra_data and cr.extra_data.get('images'):
        images = [img.get('link') for img in cr.extra_data['images'] if isinstance(img, dict) and img.get('link')]
    elif cr.image_urls:
        images = cr.image_urls
    
    return {
        "id": str(cr.id),
        "job_id": str(cr.job_id),
        "source_id": cr.source_id,
        "source_name": None,
        "category_id": cr.category_id,
        "name": cr.name,
        "city": cr.city,
        "address": cr.address,
        "latitude": float(cr.latitude) if cr.latitude else None,
        "longitude": float(cr.longitude) if cr.longitude else None,
        "phone_primary": cr.phone_primary,
        "phone_secondary": cr.phone_secondary,
        "email": cr.email,
        "website": cr.website,
        "description_short": cr.description_short,
        "rating_overall": float(cr.rating_overall) if cr.rating_overall else None,
        "review_count": cr.review_count,
        "price_min": float(cr.price_min) if cr.price_min else None,
        "price_max": float(cr.price_max) if cr.price_max else None,
        "currency": cr.currency,
        "data_completeness": float(cr.data_completeness) if cr.data_completeness else None,
        "scraper_source": cr.scraper_source,
        "thumbnail_url": cr.thumbnail_url,
        "image_urls": images,
        "amenities": cr.amenities if cr.amenities else [],
        "opening_hours": cr.opening_hours,
        "place_id": place_id,
        "images_count": images_count,
        "user_overrides": cr.user_overrides if cr.user_overrides else {},
        "validated_at": cr.updated_at.isoformat() if cr.updated_at else None,  # Use updated_at as validation time
        "created_at": cr.created_at.isoformat() if cr.created_at else None
    }


@router.get("/stats/summary")
def get_validated_stats(db: Session = Depends(get_db)):
    """
    Get summary statistics for validated results (approved cleaned_results).
    
    - Public endpoint
    - Returns total count and data quality metrics
    """
    from sqlalchemy import func
    
    # Query approved cleaned_results
    base_query = db.query(CleanedResult).filter(
        CleanedResult.status == "APPROVED"
    )
    
    # Total count
    total = base_query.count()
    
    # Count with phone
    with_phone = base_query.filter(CleanedResult.phone_primary.isnot(None)).count()
    
    # Count with website
    with_website = base_query.filter(CleanedResult.website.isnot(None)).count()
    
    # Count with rating
    with_rating = base_query.filter(CleanedResult.rating_overall.isnot(None)).count()
    
    return {
        "total": total,
        "with_phone": with_phone,
        "with_website": with_website,
        "with_rating": with_rating
    }
