"""
Job routes.
Handles scrape job creation, status polling, SSE streaming, and results retrieval.
"""
import asyncio
import json
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel, ConfigDict
import structlog

from dependencies import get_db, get_current_user
from models import User, ScrapeJob, CleanedResult
from tasks.scrape_task import scrape_task
from limiter import limiter

router = APIRouter()
logger = structlog.get_logger()


# Request/Response schemas
class GoogleMapsSettings(BaseModel):
    """Settings specific to Google Maps scraper (Go microservice)"""
    geo_coordinates: Optional[str] = None  # "lat,lon" e.g. "27.693444,85.281924"
    zoom: Optional[int] = 14  # Map zoom level (1-21)
    max_depth: Optional[int] = 20  # Scroll depth / pagination depth
    radius: Optional[float] = 0  # Search radius in km (0 = no limit)
    lang: Optional[str] = "en"  # Language code
    extract_emails: Optional[bool] = False  # Extract emails from websites
    extra_reviews: Optional[bool] = False  # Fetch extended reviews
    fast_mode: Optional[bool] = False  # Use fast HTTP mode


class CreateJobRequest(BaseModel):
    category_id: int
    location: str
    source_ids: Optional[List[int]] = None
    max_results: Optional[int] = None  # None = scrape all; integer = cap per source
    google_maps_settings: Optional[GoogleMapsSettings] = None  # Settings for Google Maps scraper
    skip_existing: Optional[bool] = False  # Skip records that already exist in database


class JobResponse(BaseModel):
    id: str
    user_id: int
    category_id: int
    location: str
    source_ids: Optional[List[int]]
    max_results: Optional[int]
    status: str
    error_message: Optional[str]
    celery_task_id: Optional[str]
    started_at: Optional[str]
    completed_at: Optional[str]
    created_at: str
    
    model_config = ConfigDict(from_attributes=True)


class JobStatusResponse(BaseModel):
    id: str
    status: str
    location: str
    created_at: str
    started_at: Optional[str]
    completed_at: Optional[str]
    result_count: Optional[int]
    statistics: Optional[dict] = None  # Scraping statistics (raw_scraped, new_records, duplicates, by_source_name)
    scraping_progress: Optional[str] = None  # Live progress message during scraping


class CleanedResultResponse(BaseModel):
    id: str
    name: Optional[str]
    city: Optional[str]
    address: Optional[str]
    rating_overall: Optional[float]
    price_min: Optional[float]
    currency: Optional[str]
    data_completeness: Optional[float]
    status: str
    scraper_source: Optional[str] = None  # Optional - older results may not have this
    thumbnail_url: Optional[str] = None  # For displaying images
    latitude: Optional[float] = None  # For map display
    longitude: Optional[float] = None  # For map display
    phone_primary: Optional[str] = None  # For map popup
    created_at: str
    # Phase 6A — merge fields
    merged_from_sources: Optional[List[int]] = None
    confidence_score: Optional[float] = None
    merged_at: Optional[str] = None
    # Duplicate tracking fields
    is_new_record: Optional[bool] = True  # Default to True for backwards compatibility
    is_updated_record: Optional[bool] = False  # Default to False
    
    model_config = ConfigDict(from_attributes=True)


class PaginatedJobsResponse(BaseModel):
    items: List[JobResponse]
    total: int
    page: int
    page_size: int
    pages: int


class PaginatedResultsResponse(BaseModel):
    items: List[CleanedResultResponse]
    total: int
    page: int
    page_size: int
    pages: int


@router.post("/", status_code=status.HTTP_201_CREATED)
@limiter.limit("200/hour")  # Increased for bulk collection
async def create_job(
    request: Request,
    job_request: CreateJobRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new scrape job.
    
    - Validates request body (category_id, location, source_ids)
    - Inserts ScrapeJob with status QUEUED
    - Dispatches scrape_task to Celery (routes to mock or real based on MOCK_MODE)
    - Stores celery_task_id
    - Emits job.created log
    - Rate limited to 10 requests per hour per user
    """
    # Create scrape job
    job = ScrapeJob(
        user_id=current_user.id,
        category_id=job_request.category_id,
        location=job_request.location,
        source_ids=job_request.source_ids,
        max_results=job_request.max_results,
        google_maps_settings=job_request.google_maps_settings.model_dump() if job_request.google_maps_settings else None,
        skip_existing=job_request.skip_existing or False,
        status="QUEUED"
    )
    
    db.add(job)
    db.commit()
    db.refresh(job)
    
    # Store IDs and initial status before task dispatch (objects may become detached after task runs in eager mode)
    job_id = str(job.id)
    job_uuid = job.id
    initial_status = job.status  # Save initial status before task runs
    user_id = current_user.id
    category_id = job_request.category_id
    location = job_request.location
    
    # Dispatch Celery task
    task = scrape_task.delay(job_id)
    
    # Re-query job to get fresh instance (Celery task may have modified it)
    job = db.query(ScrapeJob).filter(ScrapeJob.id == job_uuid).first()
    
    # Store celery_task_id
    job.celery_task_id = task.id
    db.commit()
    
    logger.info("job.created", job_id=job_id, user_id=user_id,
                category_id=category_id, location=location)
    
    return {
        "id": job_id,
        "status": initial_status,  # Return initial status, not final status
        "celery_task_id": task.id,
        "message": "Job created and queued successfully"
    }


@router.get("/", response_model=PaginatedJobsResponse)
def get_jobs(
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get paginated job history for current user.
    
    - Default page_size=20, max page_size=100
    - Ordered by created_at DESC
    """
    # Validate and cap page_size
    if page_size > 100:
        page_size = 100
    if page_size < 1:
        page_size = 20
    if page < 1:
        page = 1
    
    # Query jobs for current user
    query = db.query(ScrapeJob).filter(ScrapeJob.user_id == current_user.id)
    
    # Get total count
    total = query.count()
    
    # Get paginated results
    jobs = query.order_by(ScrapeJob.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    
    # Calculate total pages
    pages = -(-total // page_size) if total > 0 else 0  # Ceiling division
    
    # Convert jobs to dict format with proper string conversions
    items = []
    for job in jobs:
        items.append({
            "id": str(job.id),
            "user_id": job.user_id,
            "category_id": job.category_id,
            "location": job.location,
            "source_ids": job.source_ids,
            "max_results": job.max_results,
            "status": job.status,
            "error_message": job.error_message,
            "celery_task_id": job.celery_task_id,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "created_at": job.created_at.isoformat() if job.created_at else None
        })
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": pages
    }


@router.get("/{job_id}/status", response_model=JobStatusResponse)
def get_job_status(
    job_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get job status and result count.
    
    - Returns job status, timestamps, and result count if DONE
    - Returns 404 if job not found or doesn't belong to user
    """
    job = db.query(ScrapeJob).filter(
        ScrapeJob.id == job_id,
        ScrapeJob.user_id == current_user.id
    ).first()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    # Get result count if job is done
    result_count = None
    if job.status == "DONE":
        result_count = db.query(func.count(CleanedResult.id)).filter(
            CleanedResult.job_id == job_id
        ).scalar()
    
    return {
        "id": str(job.id),
        "status": job.status,
        "location": job.location,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "result_count": result_count,
        "statistics": job.statistics,  # Include statistics if available
        "scraping_progress": job.scraping_progress  # Include live progress message
    }


@router.get("/{job_id}/stream")
async def stream_job_status(
    job_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    SSE endpoint for real-time job status updates.
    
    - Polls database every 2 seconds
    - Yields event: status with job data
    - Breaks on DONE or FAILED
    - Checks request.is_disconnected() each iteration
    - Catches asyncio.CancelledError and exits cleanly
    """
    # Verify job exists and belongs to user
    job = db.query(ScrapeJob).filter(
        ScrapeJob.id == job_id,
        ScrapeJob.user_id == current_user.id
    ).first()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    async def event_generator():
        # Create a new database session for the SSE stream (don't use injected db)
        from database import SessionLocal
        stream_db = SessionLocal()
        
        try:
            # Send initial connection event
            yield ": connected\n\n"
            
            while True:
                # Check if client disconnected
                if await request.is_disconnected():
                    logger.info("sse.client_disconnected", job_id=str(job_id))
                    break
                
                # Re-query job from database with dedicated session
                current_job = stream_db.query(ScrapeJob).filter(ScrapeJob.id == job_id).first()
                
                if not current_job:
                    logger.error("sse.job_not_found", job_id=str(job_id))
                    break
                
                # Prepare event data
                event_data = {
                    "status": current_job.status,
                    "started_at": current_job.started_at.isoformat() if current_job.started_at else None,
                    "completed_at": current_job.completed_at.isoformat() if current_job.completed_at else None,
                    "scraping_progress": current_job.scraping_progress,  # Add live progress
                }
                
                # Add statistics if available (for both RUNNING and DONE status)
                if current_job.statistics:
                    event_data["statistics"] = current_job.statistics
                
                # Add result count if done
                if current_job.status == "DONE":
                    result_count = stream_db.query(func.count(CleanedResult.id)).filter(
                        CleanedResult.job_id == job_id
                    ).scalar()
                    event_data["result_count"] = result_count
                
                # Add error message if failed
                if current_job.status == "FAILED":
                    event_data["error"] = current_job.error_message
                
                # Yield SSE event with proper formatting
                event_message = f"event: status\ndata: {json.dumps(event_data)}\n\n"
                yield event_message
                
                # Break if job is done or failed
                if current_job.status in ("DONE", "FAILED"):
                    # Send final event to signal completion
                    yield ": complete\n\n"
                    break
                
                # Wait 2 seconds before next poll
                await asyncio.sleep(2)
                
        except asyncio.CancelledError:
            # Client disconnected, exit cleanly without re-raising
            logger.info("sse.cancelled", job_id=str(job_id))
            return
        except Exception as e:
            # Log any other errors
            logger.error("sse.error", job_id=str(job_id), error=str(e), exc_info=True)
            # Send error event
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
            return
        finally:
            # Always close the dedicated database session
            stream_db.close()
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Content-Type": "text/event-stream; charset=utf-8",
        }
    )


@router.get("/{job_id}/results", response_model=PaginatedResultsResponse)
def get_job_results(
    job_id: UUID,
    page: int = 1,
    page_size: int = 50,
    filter_type: str = "all",  # all, new, updated, duplicates
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get paginated cleaned results for a job with optional filtering.
    
    - Default page_size=50, max page_size=200
    - Ordered by created_at DESC
    - Returns 404 if job not found or doesn't belong to user
    - filter_type: all, new, updated, duplicates
    """
    # Verify job exists and belongs to user
    job = db.query(ScrapeJob).filter(
        ScrapeJob.id == job_id,
        ScrapeJob.user_id == current_user.id
    ).first()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    # Validate and cap page_size
    if page_size > 200:
        page_size = 200
    if page_size < 1:
        page_size = 50
    if page < 1:
        page = 1
    
    # Query results for this job
    query = db.query(CleanedResult).filter(CleanedResult.job_id == job_id)
    
    # Apply filters based on filter_type
    if filter_type == "new":
        query = query.filter(CleanedResult.is_new_record == True)
    elif filter_type == "updated":
        query = query.filter(CleanedResult.is_updated_record == True)
    elif filter_type == "duplicates":
        query = query.filter(
            CleanedResult.is_new_record == False,
            CleanedResult.is_updated_record == False
        )
    # else: filter_type == "all" - no additional filter
    
    # Get total count
    total = query.count()
    
    # Get paginated results
    results = query.order_by(CleanedResult.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    
    # Calculate total pages
    pages = -(-total // page_size) if total > 0 else 0  # Ceiling division
    
    # Convert UUIDs to strings for response
    items = []
    for result in results:
        items.append({
            "id": str(result.id),
            "name": result.name,
            "city": result.city,
            "address": result.address,
            "rating_overall": float(result.rating_overall) if result.rating_overall else None,
            "price_min": float(result.price_min) if result.price_min else None,
            "currency": result.currency,
            "data_completeness": float(result.data_completeness) if result.data_completeness else None,
            "status": result.status,
            "scraper_source": result.scraper_source,
            "thumbnail_url": result.thumbnail_url,
            "latitude": float(result.latitude) if result.latitude else None,
            "longitude": float(result.longitude) if result.longitude else None,
            "phone_primary": result.phone_primary,
            "created_at": result.created_at.isoformat() if result.created_at else None,
            "is_new_record": result.is_new_record,
            "is_updated_record": result.is_updated_record
        })
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": pages
    }


@router.post("/{job_id}/cancel")
async def cancel_job(
    job_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Cancel a running scrape job.
    
    - Verifies job exists and belongs to user
    - Only works for QUEUED or RUNNING jobs
    - Revokes Celery task with SIGTERM signal
    - Updates job status to CANCELLED
    - Partial results collected so far are saved
    """
    # Fetch job
    job = db.query(ScrapeJob).filter(
        ScrapeJob.id == job_id,
        ScrapeJob.user_id == current_user.id
    ).first()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    # Check if job can be cancelled
    if job.status not in ["QUEUED", "RUNNING"]:
        return {
            "success": False,
            "message": f"Job cannot be cancelled. Current status: {job.status}",
            "status": job.status
        }
    
    # Revoke Celery task
    if job.celery_task_id:
        from celery.result import AsyncResult
        AsyncResult(job.celery_task_id).revoke(terminate=True, signal='SIGTERM')
        logger.info("job.cancelled", job_id=str(job_id), celery_task_id=job.celery_task_id)
    
    # Update job status
    job.status = "CANCELLED"
    job.completed_at = datetime.utcnow()
    job.error_message = "Cancelled by user"
    db.commit()
    
    return {
        "success": True,
        "job_id": str(job_id),
        "status": "CANCELLED",
        "message": "Job cancelled successfully. Partial results have been saved."
    }


@router.post("/{job_id}/retry", status_code=status.HTTP_201_CREATED)
@limiter.limit("10/hour")
async def retry_job(
    request: Request,
    job_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retry a failed scrape job.
    
    - Fetches original job by ID and verifies user ownership
    - Returns 404 if job not found
    - Returns 403 if user does not own the job
    - Returns 400 if job status is not FAILED
    - Creates new job with same category_id, location, and source_ids
    - Sets new job status to QUEUED
    - Dispatches Celery task for new job
    - Returns new job ID and status
    - Rate limited to 10 requests per hour per user (same as job creation)
    """
    # Fetch original job
    original_job = db.query(ScrapeJob).filter(
        ScrapeJob.id == job_id
    ).first()
    
    # Check if job exists
    if not original_job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    # Check if user owns the job
    if original_job.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to retry this job"
        )
    
    # Check if job status is FAILED
    if original_job.status != "FAILED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Only FAILED jobs can be retried. Current status: {original_job.status}"
        )
    
    # Create new job with same parameters
    new_job = ScrapeJob(
        user_id=current_user.id,
        category_id=original_job.category_id,
        location=original_job.location,
        source_ids=original_job.source_ids,
        max_results=original_job.max_results,
        status="QUEUED"
    )
    
    db.add(new_job)
    db.commit()
    db.refresh(new_job)
    
    # Store IDs before task dispatch
    new_job_id = str(new_job.id)
    new_job_uuid = new_job.id
    initial_status = new_job.status
    
    # Dispatch Celery task
    task = scrape_task.delay(new_job_id)
    
    # Re-query job to get fresh instance
    new_job = db.query(ScrapeJob).filter(ScrapeJob.id == new_job_uuid).first()
    
    # Store celery_task_id
    new_job.celery_task_id = task.id
    db.commit()
    
    logger.info("job.retried", 
                original_job_id=str(job_id),
                new_job_id=new_job_id,
                user_id=current_user.id,
                category_id=original_job.category_id,
                location=original_job.location)
    
    return {
        "id": new_job_id,
        "status": initial_status,
        "celery_task_id": task.id,
        "message": "Job retried successfully",
        "original_job_id": str(job_id)
    }


@router.get("/results/{result_id}")
def get_result_detail(
    result_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get full details for a single cleaned result.
    
    - Returns all 89 fields from CleanedResult model
    - Auth required (user must be logged in)
    - No admin role required — regular users can view results
    - Returns 404 if result not found
    """
    result = db.query(CleanedResult).filter(CleanedResult.id == result_id).first()
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Result not found"
        )
    
    # Explicitly serialize to ensure JSONB fields are properly converted
    return {
        "id": str(result.id),
        "job_id": str(result.job_id),
        "source_id": result.source_id,
        "category_id": result.category_id,
        "dedup_key": result.dedup_key,
        # Identity
        "name": result.name,
        "brand": result.brand,
        "property_type": result.property_type,
        "star_rating": result.star_rating,
        # Location
        "address": result.address,
        "street_address": result.street_address,
        "city": result.city,
        "district": result.district,
        "province": result.province,
        "country": result.country,
        "latitude": float(result.latitude) if result.latitude else None,
        "longitude": float(result.longitude) if result.longitude else None,
        "neighbourhood": result.neighbourhood,
        "nearby_landmark": result.nearby_landmark,
        # Contact
        "phone_primary": result.phone_primary,
        "phone_secondary": result.phone_secondary,
        "email": result.email,
        "website": result.website,
        "facebook_url": result.facebook_url,
        "instagram_handle": result.instagram_handle,
        "whatsapp_number": result.whatsapp_number,
        # Pricing
        "price_min": float(result.price_min) if result.price_min else None,
        "price_max": float(result.price_max) if result.price_max else None,
        "currency": result.currency,
        "price_range_label": result.price_range_label,
        "includes_breakfast": result.includes_breakfast,
        "includes_taxes": result.includes_taxes,
        # Reviews
        "rating_overall": float(result.rating_overall) if result.rating_overall else None,
        "rating_label": result.rating_label,
        "review_count": result.review_count,
        "rating_cleanliness": float(result.rating_cleanliness) if result.rating_cleanliness else None,
        "rating_location": float(result.rating_location) if result.rating_location else None,
        "rating_facilities": float(result.rating_facilities) if result.rating_facilities else None,
        "rating_service": float(result.rating_service) if result.rating_service else None,
        "rating_value": float(result.rating_value) if result.rating_value else None,
        # Facilities
        "amenities": result.amenities or [],
        "pets_allowed": result.pets_allowed,
        "breakfast_available": result.breakfast_available,
        "checkin_time": result.checkin_time,
        "checkout_time": result.checkout_time,
        "cancellation_policy": result.cancellation_policy,
        "free_cancellation": result.free_cancellation,
        # Media
        "thumbnail_url": result.thumbnail_url,
        "image_urls": result.image_urls or [],
        "image_count": result.image_count,
        # Content
        "description_short": result.description_short,
        "description_full": result.description_full,
        "highlights": result.highlights or [],
        "popular_with": result.popular_with or [],
        "staff_languages": result.staff_languages or [],
        # Business Info
        "opening_hours": result.opening_hours,
        "established_year": result.established_year,
        # Metadata
        "source_url": result.source_url,
        "source_listing_id": result.source_listing_id,
        "data_completeness": float(result.data_completeness) if result.data_completeness else None,
        "is_edited": result.is_edited,
        "is_duplicate": result.is_duplicate,
        "status": result.status,
        "scraper_source": result.scraper_source,
        "extra_data": result.extra_data or {},
        "created_at": result.created_at.isoformat() if result.created_at else None,
        "updated_at": result.updated_at.isoformat() if result.updated_at else None,
        # Merge tracking
        "merged_from_sources": result.merged_from_sources or [],
        "confidence_score": float(result.confidence_score) if result.confidence_score else None,
        "merged_at": result.merged_at.isoformat() if result.merged_at else None,
    }



@router.get("/go-scraper/queue")
async def get_go_scraper_queue_status(
    current_user: User = Depends(get_current_user)
):
    """
    Get Go scraper pool queue status for monitoring.
    
    Returns:
        - Total instances (4)
        - Healthy instances count
        - Total pending/working/completed/failed across all instances
        - Per-instance status breakdown
    
    Requires authentication but no admin role.
    """
    from scrapers.go_scraper_pool import go_scraper_pool
    
    # Get status from all instances in the pool
    pool_status = await go_scraper_pool.get_all_queue_status()
    
    return pool_status


@router.get("/results/{result_id}/duplicate-history")
def get_duplicate_history(
    result_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get the original job that first scraped this duplicate record.
    
    Returns:
    - is_duplicate: Boolean indicating if this is a duplicate
    - original_job_id: UUID of the first job that scraped this record
    - original_job_date: When the original job was completed
    - original_job_location: Location of the original job
    - dedup_key: The dedup_key used to identify duplicates
    
    Returns 404 if result not found.
    Returns 403 if result doesn't belong to user's job.
    """
    # Load the current result
    current_result = db.query(CleanedResult).filter(
        CleanedResult.id == result_id
    ).first()
    
    if not current_result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Result not found"
        )
    
    # Verify ownership (result belongs to job belonging to user)
    job = db.query(ScrapeJob).filter(
        ScrapeJob.id == current_result.job_id,
        ScrapeJob.user_id == current_user.id
    ).first()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # If not a duplicate, return early
    if current_result.is_new_record or current_result.is_updated_record:
        return {
            "is_duplicate": False,
            "original_job_id": None,
            "original_job_date": None,
            "original_job_location": None,
            "dedup_key": current_result.dedup_key
        }
    
    # Find the original record (first record with same dedup_key)
    original_result = db.query(CleanedResult).join(
        ScrapeJob, CleanedResult.job_id == ScrapeJob.id
    ).filter(
        CleanedResult.dedup_key == current_result.dedup_key,
        ScrapeJob.user_id == current_user.id,  # Same user's jobs
        CleanedResult.created_at < current_result.created_at  # Earlier record
    ).order_by(
        CleanedResult.created_at.asc()  # Get the earliest
    ).first()
    
    if not original_result:
        # Shouldn't happen, but handle gracefully
        return {
            "is_duplicate": True,
            "original_job_id": None,
            "original_job_date": None,
            "original_job_location": "Unknown",
            "dedup_key": current_result.dedup_key
        }
    
    # Load original job details
    original_job = db.query(ScrapeJob).filter(
        ScrapeJob.id == original_result.job_id
    ).first()
    
    return {
        "is_duplicate": True,
        "original_job_id": str(original_job.id),
        "original_job_date": original_job.completed_at.isoformat() if original_job.completed_at else None,
        "original_job_location": original_job.location,
        "dedup_key": current_result.dedup_key
    }
