"""
Job routes.
Handles scrape job creation, status polling, SSE streaming, and results retrieval.
"""
import asyncio
import json
from typing import List, Optional
from uuid import UUID
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
class CreateJobRequest(BaseModel):
    category_id: int
    location: str
    source_ids: Optional[List[int]] = None
    max_results: Optional[int] = None  # None = scrape all; integer = cap per source


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
    created_at: str
    # Phase 6A — merge fields
    merged_from_sources: Optional[List[int]] = None
    confidence_score: Optional[float] = None
    merged_at: Optional[str] = None
    
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
        "result_count": result_count
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
        try:
            # Send initial connection event
            yield ": connected\n\n"
            
            while True:
                # Check if client disconnected
                if await request.is_disconnected():
                    logger.info("sse.client_disconnected", job_id=str(job_id))
                    break
                
                # Refresh job status from database
                db.refresh(job)
                
                # Prepare event data
                event_data = {
                    "status": job.status,
                    "started_at": job.started_at.isoformat() if job.started_at else None,
                    "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                }
                
                # Add result count if done
                if job.status == "DONE":
                    result_count = db.query(func.count(CleanedResult.id)).filter(
                        CleanedResult.job_id == job_id
                    ).scalar()
                    event_data["result_count"] = result_count
                
                # Add error message if failed
                if job.status == "FAILED":
                    event_data["error"] = job.error_message
                
                # Yield SSE event with proper formatting
                event_message = f"event: status\ndata: {json.dumps(event_data)}\n\n"
                yield event_message
                
                # Break if job is done or failed
                if job.status in ("DONE", "FAILED"):
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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get paginated cleaned results for a job.
    
    - Default page_size=50, max page_size=200
    - Ordered by created_at DESC
    - Returns 404 if job not found or doesn't belong to user
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
            "created_at": result.created_at.isoformat() if result.created_at else None
        })
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": pages
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
    
    return result
