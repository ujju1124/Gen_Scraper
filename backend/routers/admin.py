"""
Admin routes.
Handles admin-only operations like viewing all results with filtering and sorting.
"""
from typing import List, Optional
from datetime import datetime
import csv
import json
from io import StringIO
from fastapi import APIRouter, Depends, Query, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict

from dependencies import get_db, require_admin
from models import User, CleanedResult
from tasks.merge_task import merge_all_sources

router = APIRouter()


# User management schemas
class UserResponse(BaseModel):
    id: int
    email: str
    role: str
    is_active: bool
    created_at: str
    
    model_config = ConfigDict(from_attributes=True)


class PaginatedUsersResponse(BaseModel):
    items: List[UserResponse]
    total: int
    page: int
    page_size: int
    pages: int


class UpdateUserStatusRequest(BaseModel):
    is_active: bool


# Response schemas
class AdminResultResponse(BaseModel):
    id: str
    job_id: str
    source_id: int
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
    price_min: Optional[float]
    currency: Optional[str]
    data_completeness: Optional[float]
    status: str
    created_at: str
    
    model_config = ConfigDict(from_attributes=True)


class PaginatedAdminResultsResponse(BaseModel):
    items: List[AdminResultResponse]
    total: int
    page: int
    page_size: int
    pages: int


@router.get("/export")
def export_admin_results(
    format: str = Query("csv", description="Export format: csv or json"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status (PENDING, APPROVED, REJECTED)"),
    category_id: Optional[int] = Query(None, description="Filter by category ID"),
    city: Optional[str] = Query(None, description="Filter by city name"),
    sort_by: str = Query("created_at", description="Sort by field (data_completeness or created_at)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Export filtered admin results as CSV or JSON.
    
    - Protected by require_admin dependency
    - Accepts same filters as GET /results/
    - format: 'csv' or 'json'
    - Maximum 10,000 results per export
    - Returns file download with appropriate Content-Type and Content-Disposition headers
    """
    # Validate format
    if format not in ["csv", "json"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid format. Must be 'csv' or 'json'"
        )
    
    # Build query (same as get_admin_results)
    query = db.query(CleanedResult)
    
    # Apply filters
    if status_filter:
        query = query.filter(CleanedResult.status == status_filter)
    
    if category_id:
        query = query.filter(CleanedResult.category_id == category_id)
    
    if city:
        query = query.filter(CleanedResult.city.ilike(f"%{city}%"))
    
    # Apply sorting
    if sort_by == "data_completeness":
        query = query.order_by(CleanedResult.data_completeness.desc())
    else:  # default to created_at
        query = query.order_by(CleanedResult.created_at.desc())
    
    # Check count before fetching
    total = query.count()
    
    if total > 10000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Export limit exceeded. Found {total} results, maximum is 10,000. Please apply more filters."
        )
    
    # Fetch all results (up to 10,000)
    results = query.limit(10000).all()
    
    # Generate timestamp for filename
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    
    if format == "csv":
        return export_as_csv(results, timestamp)
    else:  # json
        return export_as_json(results, timestamp, total)


def export_as_csv(results: List[CleanedResult], timestamp: str) -> StreamingResponse:
    """
    Generate CSV export with headers and formatted data.
    Includes latitude and longitude coordinates from Phase 4B geocoding.
    """
    # Create CSV in memory
    output = StringIO()
    writer = csv.writer(output)
    
    # Write headers (Phase 4B: Added Latitude and Longitude)
    headers = [
        "ID", "Job ID", "Source ID", "Category ID", "Name", "City", "Address",
        "Latitude", "Longitude", "Phone Primary", "Phone Secondary", "Email", "Website", "Description",
        "Rating", "Price Min", "Currency", "Data Completeness (%)", "Status", "Created At"
    ]
    writer.writerow(headers)
    
    # Write data rows
    for result in results:
        writer.writerow([
            str(result.id),
            str(result.job_id),
            result.source_id,
            result.category_id,
            result.name or "",
            result.city or "",
            result.address or "",
            float(result.latitude) if result.latitude else "",
            float(result.longitude) if result.longitude else "",
            result.phone_primary or "",
            result.phone_secondary or "",
            result.email or "",
            result.website or "",
            result.description_short or "",
            float(result.rating_overall) if result.rating_overall else "",
            float(result.price_min) if result.price_min else "",
            result.currency or "",
            float(result.data_completeness) if result.data_completeness else "",
            result.status,
            result.created_at.isoformat() if result.created_at else ""
        ])
    
    # Get CSV content
    csv_content = output.getvalue()
    output.close()
    
    # Return as streaming response
    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=results_{timestamp}.csv"
        }
    )


def export_as_json(results: List[CleanedResult], timestamp: str, total: int) -> StreamingResponse:
    """
    Generate JSON export with metadata and results array.
    Phase 4B: Includes latitude, longitude, and geocoding metadata.
    """
    # Count geocoded results
    geocoded_count = sum(1 for r in results if r.latitude is not None and r.longitude is not None)
    geocoding_success_rate = (geocoded_count / total * 100) if total > 0 else 0
    
    # Build JSON structure
    data = {
        "metadata": {
            "exported_at": datetime.utcnow().isoformat(),
            "total_count": total,
            "geocoded_count": geocoded_count,
            "geocoding_success_rate": f"{geocoding_success_rate:.1f}%",
            "format": "json"
        },
        "results": []
    }
    
    # Add results (Phase 4B: Added latitude and longitude)
    for result in results:
        data["results"].append({
            "id": str(result.id),
            "job_id": str(result.job_id),
            "source_id": result.source_id,
            "category_id": result.category_id,
            "name": result.name,
            "city": result.city,
            "address": result.address,
            "latitude": float(result.latitude) if result.latitude else None,
            "longitude": float(result.longitude) if result.longitude else None,
            "phone_primary": result.phone_primary,
            "phone_secondary": result.phone_secondary,
            "email": result.email,
            "website": result.website,
            "description_short": result.description_short,
            "rating_overall": float(result.rating_overall) if result.rating_overall else None,
            "price_min": float(result.price_min) if result.price_min else None,
            "currency": result.currency,
            "data_completeness": float(result.data_completeness) if result.data_completeness else None,
            "status": result.status,
            "created_at": result.created_at.isoformat() if result.created_at else None
        })
    
    # Convert to JSON string
    json_content = json.dumps(data, indent=2)
    
    # Return as streaming response
    return StreamingResponse(
        iter([json_content]),
        media_type="application/json",
        headers={
            "Content-Disposition": f"attachment; filename=results_{timestamp}.json"
        }
    )


@router.get("/results/", response_model=PaginatedAdminResultsResponse)
def get_admin_results(
    status: Optional[str] = Query(None, description="Filter by status (PENDING, APPROVED, REJECTED)"),
    category_id: Optional[int] = Query(None, description="Filter by category ID"),
    city: Optional[str] = Query(None, description="Filter by city name"),
    sort_by: str = Query("created_at", description="Sort by field (data_completeness or created_at)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Page size (max 200)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Get paginated cleaned results for admin review.
    
    - Protected by require_admin dependency
    - Accepts query params: status, category_id, city, sort_by, page, page_size
    - sort_by can be 'data_completeness' or 'created_at'
    - Default page_size=50, max page_size=200
    - Returns paginated envelope with items, total, page, page_size, pages
    """
    # Build query
    query = db.query(CleanedResult)
    
    # Apply filters
    if status:
        query = query.filter(CleanedResult.status == status)
    
    if category_id:
        query = query.filter(CleanedResult.category_id == category_id)
    
    if city:
        query = query.filter(CleanedResult.city.ilike(f"%{city}%"))
    
    # Apply sorting
    if sort_by == "data_completeness":
        query = query.order_by(CleanedResult.data_completeness.desc())
    else:  # default to created_at
        query = query.order_by(CleanedResult.created_at.desc())
    
    # Get total count
    total = query.count()
    
    # Get paginated results
    results = query.offset((page - 1) * page_size).limit(page_size).all()
    
    # Calculate total pages
    pages = -(-total // page_size) if total > 0 else 0  # Ceiling division
    
    # Convert to response format (Phase 4B: Added latitude and longitude)
    items = []
    for result in results:
        items.append({
            "id": str(result.id),
            "job_id": str(result.job_id),
            "source_id": result.source_id,
            "category_id": result.category_id,
            "name": result.name,
            "city": result.city,
            "address": result.address,
            "latitude": float(result.latitude) if result.latitude else None,
            "longitude": float(result.longitude) if result.longitude else None,
            "phone_primary": result.phone_primary,
            "phone_secondary": result.phone_secondary,
            "email": result.email,
            "website": result.website,
            "description_short": result.description_short,
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


# Bulk action schemas
class BulkActionRequest(BaseModel):
    ids: List[str]
    action: str  # "approve" or "reject"


class BulkActionResponse(BaseModel):
    processed: int
    action: str


@router.post("/results/bulk-action", response_model=BulkActionResponse)
def bulk_action_results(
    request: BulkActionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Bulk approve or reject multiple results.
    
    - Admin only (role loaded from DB via require_admin)
    - Body: {"ids": ["uuid1", "uuid2", ...], "action": "approve" | "reject"}
    - Returns: {"processed": N, "action": "approve"|"reject"}
    - Processes all IDs in single DB transaction
    - Skips IDs that don't exist — doesn't crash
    - Returns 400 if ids list is empty or action is invalid
    """
    # Validate request
    if not request.ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ids list cannot be empty"
        )
    
    if request.action not in ["approve", "reject"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="action must be 'approve' or 'reject'"
        )
    
    # Convert string IDs to UUIDs and filter out invalid ones
    from uuid import UUID
    valid_ids = []
    for id_str in request.ids:
        try:
            valid_ids.append(UUID(id_str))
        except (ValueError, AttributeError):
            # Skip invalid UUIDs
            continue
    
    if not valid_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid UUIDs provided"
        )
    
    # Determine target status
    target_status = "APPROVED" if request.action == "approve" else "REJECTED"
    
    # Update all matching results in a single transaction
    updated_count = db.query(CleanedResult).filter(
        CleanedResult.id.in_(valid_ids)
    ).update(
        {"status": target_status},
        synchronize_session=False
    )
    
    db.commit()
    
    return {
        "processed": updated_count,
        "action": request.action
    }



# User Management Endpoints

@router.get("/users", response_model=PaginatedUsersResponse)
def get_users(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size (max 100)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Get paginated list of all users.
    
    - Admin only (role loaded from DB via require_admin)
    - Returns: email, role, is_active, created_at, id
    - Query params: page, page_size
    - Default page_size=20, max page_size=100
    """
    # Build query
    query = db.query(User).order_by(User.created_at.desc())
    
    # Get total count
    total = query.count()
    
    # Get paginated results
    users = query.offset((page - 1) * page_size).limit(page_size).all()
    
    # Calculate total pages
    pages = -(-total // page_size) if total > 0 else 0  # Ceiling division
    
    # Convert to response format
    items = []
    for user in users:
        items.append({
            "id": user.id,
            "email": user.email,
            "role": user.role,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat() if user.created_at else None
        })
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": pages
    }


@router.patch("/users/{user_id}", response_model=UserResponse)
def update_user_status(
    user_id: int,
    request: UpdateUserStatusRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Update user active status.
    
    - Admin only (role loaded from DB via require_admin)
    - Body: {"is_active": bool}
    - Prevents admin from deactivating their own account → returns 400
    - Returns updated user
    """
    # Prevent admin from deactivating their own account
    if user_id == current_user.id and not request.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own account"
        )
    
    # Find user
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update status
    user.is_active = request.is_active
    db.commit()
    db.refresh(user)
    
    return {
        "id": user.id,
        "email": user.email,
        "role": user.role,
        "is_active": user.is_active,
        "created_at": user.created_at.isoformat() if user.created_at else None
    }



# Monitoring schemas
class ScraperHealthItem(BaseModel):
    source_id: int
    source_name: str
    is_active: bool
    last_job_status: Optional[str]
    result_count: int


class MonitoringResponse(BaseModel):
    job_success_rate: float
    scraper_health: List[ScraperHealthItem]
    results_per_source: dict
    avg_job_duration_seconds: Optional[float]
    total_results: dict
    recent_failures: List[dict]


@router.get("/monitoring", response_model=MonitoringResponse)
def get_monitoring_data(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Get monitoring dashboard data.
    
    - Admin only (role loaded from DB via require_admin)
    - Returns:
      - job_success_rate: percentage of DONE jobs vs total jobs
      - scraper_health: list of sources with active/inactive/last_job_status
      - results_per_source: count of cleaned_results grouped by source
      - avg_job_duration_seconds: average time from job creation to completion
      - total_results: {raw: N, cleaned: N, validated: N}
      - recent_failures: last 5 failed jobs with source and error info
    """
    from models import ScrapeJob, RawResult, ValidatedResult, Source
    from sqlalchemy import func, case
    
    # 1. Job success rate
    total_jobs = db.query(func.count(ScrapeJob.id)).scalar() or 0
    done_jobs = db.query(func.count(ScrapeJob.id)).filter(
        ScrapeJob.status == "DONE"
    ).scalar() or 0
    
    job_success_rate = (done_jobs / total_jobs * 100) if total_jobs > 0 else 0.0
    
    # 2. Scraper health
    sources = db.query(Source).all()
    scraper_health = []
    
    for source in sources:
        # Get last job status for this source
        # Use PostgreSQL array operator @> for "contains"
        last_job = db.query(ScrapeJob).filter(
            ScrapeJob.source_ids.isnot(None),
            func.array_position(ScrapeJob.source_ids, source.id).isnot(None)
        ).order_by(ScrapeJob.created_at.desc()).first()
        
        last_job_status = last_job.status if last_job else None
        
        # Count results for this source
        result_count = db.query(func.count(CleanedResult.id)).filter(
            CleanedResult.source_id == source.id
        ).scalar() or 0
        
        scraper_health.append({
            "source_id": source.id,
            "source_name": source.name,
            "is_active": source.is_active,
            "last_job_status": last_job_status,
            "result_count": result_count
        })
    
    # 3. Results per source
    results_per_source_query = db.query(
        Source.name,
        func.count(CleanedResult.id).label("count")
    ).join(
        CleanedResult, CleanedResult.source_id == Source.id
    ).group_by(Source.name).all()
    
    results_per_source = {name: count for name, count in results_per_source_query}
    
    # 4. Average job duration
    completed_jobs = db.query(
        func.avg(
            func.extract('epoch', ScrapeJob.completed_at - ScrapeJob.created_at)
        )
    ).filter(
        ScrapeJob.status == "DONE",
        ScrapeJob.completed_at.isnot(None)
    ).scalar()
    
    avg_job_duration_seconds = float(completed_jobs) if completed_jobs else None
    
    # 5. Total results
    total_raw = db.query(func.count(RawResult.id)).scalar() or 0
    total_cleaned = db.query(func.count(CleanedResult.id)).scalar() or 0
    total_validated = db.query(func.count(ValidatedResult.id)).scalar() or 0
    
    total_results = {
        "raw": total_raw,
        "cleaned": total_cleaned,
        "validated": total_validated
    }
    
    # 6. Recent failures
    failed_jobs = db.query(ScrapeJob).filter(
        ScrapeJob.status == "FAILED"
    ).order_by(ScrapeJob.created_at.desc()).limit(5).all()
    
    recent_failures = []
    for job in failed_jobs:
        # Get source names
        source_names = []
        if job.source_ids:
            sources = db.query(Source).filter(Source.id.in_(job.source_ids)).all()
            source_names = [s.name for s in sources]
        
        recent_failures.append({
            "job_id": str(job.id),
            "location": job.location,
            "sources": source_names,
            "error_message": job.error_message,
            "created_at": job.created_at.isoformat() if job.created_at else None
        })
    
    return {
        "job_success_rate": round(job_success_rate, 2),
        "scraper_health": scraper_health,
        "results_per_source": results_per_source,
        "avg_job_duration_seconds": round(avg_job_duration_seconds, 2) if avg_job_duration_seconds else None,
        "total_results": total_results,
        "recent_failures": recent_failures
    }


# Merge All Sources Endpoint (Phase 7 Priority 1 Fix)

class MergeAllSourcesResponse(BaseModel):
    task_id: str
    message: str


class MergeStatusResponse(BaseModel):
    total_records_processed: int
    exact_merged_groups: int
    exact_merged_records: int
    fuzzy_merged_groups: int
    fuzzy_merged_records: int
    total_merged_groups: int
    total_merged_records: int
    merge_rate_percent: float


@router.post("/merge-all-sources", response_model=MergeAllSourcesResponse)
def trigger_merge_all_sources(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Trigger cross-job merging of all records from different sources.
    
    - Admin only (role loaded from DB via require_admin)
    - Fixes critical bug where merging only happened within single jobs
    - Groups ALL non-duplicate cleaned_results by dedup_key across all jobs
    - Merges records from different sources that represent the same business
    - Returns task_id for tracking progress
    
    Expected merge rate: 15-20% (720-960 merged records out of 4,790)
    
    Example:
        POST /api/v1/admin/merge-all-sources
        Response: {"task_id": "abc123", "message": "Merge task started"}
    """
    # Trigger Celery task
    task = merge_all_sources.delay()
    
    return {
        "task_id": task.id,
        "message": "Cross-job merge task started. This may take several minutes for large datasets."
    }


@router.get("/merge-status", response_model=MergeStatusResponse)
def get_merge_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Get current merge statistics from database.
    
    - Admin only (role loaded from DB via require_admin)
    - Returns:
      - total_records_processed: Total cleaned_results in database
      - merged_records: Count of records with merged_from_sources
      - merge_rate_percent: Percentage of merged records
    
    Example:
        GET /api/v1/admin/merge-status
        Response: {
            "total_records_processed": 4790,
            "exact_merged_groups": 450,
            "exact_merged_records": 950,
            "fuzzy_merged_groups": 50,
            "fuzzy_merged_records": 120,
            "total_merged_groups": 500,
            "total_merged_records": 1070,
            "merge_rate_percent": 22.34
        }
    """
    from sqlalchemy import func
    
    # Get total records
    total_records = db.query(func.count(CleanedResult.id)).scalar() or 0
    
    # Get merged records count
    merged_records = db.query(func.count(CleanedResult.id)).filter(
        CleanedResult.merged_from_sources.isnot(None)
    ).scalar() or 0
    
    # Calculate merge rate
    merge_rate = (merged_records / total_records * 100) if total_records > 0 else 0.0
    
    # Note: We can't get exact/fuzzy breakdown from database alone
    # These would need to be stored in a separate merge_log table
    # For now, return total merged records
    
    return {
        "total_records_processed": total_records,
        "exact_merged_groups": 0,  # Not tracked in DB
        "exact_merged_records": 0,  # Not tracked in DB
        "fuzzy_merged_groups": 0,  # Not tracked in DB
        "fuzzy_merged_records": 0,  # Not tracked in DB
        "total_merged_groups": 0,  # Not tracked in DB
        "total_merged_records": merged_records,
        "merge_rate_percent": round(merge_rate, 2)
    }


# Self-Healing Dashboard Endpoint (Phase 7 - KEY SELLING POINT)

class HealingStatsResponse(BaseModel):
    total_attempts: int
    resolved: int
    pending: int
    success_rate: float
    avg_confidence: float
    recent_heals: List[dict]


@router.get("/healing-stats", response_model=HealingStatsResponse)
def get_healing_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Get self-healing system statistics for admin dashboard.
    
    - Admin only (role loaded from DB via require_admin)
    - Returns:
      - total_attempts: Total healing attempts
      - resolved: Successfully healed selectors
      - pending: Selectors awaiting manual review
      - success_rate: Percentage of resolved heals
      - avg_confidence: Average confidence score for resolved heals
      - recent_heals: Last 20 healing attempts with details
    
    This is a KEY SELLING POINT - shows the self-healing system in action!
    
    Example:
        GET /api/v1/admin/healing-stats
        Response: {
            "total_attempts": 109,
            "resolved": 21,
            "pending": 88,
            "success_rate": 19.3,
            "avg_confidence": 0.83,
            "recent_heals": [...]
        }
    """
    from sqlalchemy import text
    
    # Get overall stats
    stats_query = text("""
        SELECT 
            COUNT(*) as total,
            COUNT(CASE WHEN status='RESOLVED' THEN 1 END) as resolved,
            COUNT(CASE WHEN status='PENDING' THEN 1 END) as pending,
            ROUND(COUNT(CASE WHEN status='RESOLVED' THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0), 1) as success_rate,
            ROUND(AVG(CASE WHEN status='RESOLVED' THEN confidence END), 2) as avg_confidence
        FROM selector_heal_log
    """)
    stats = db.execute(stats_query).fetchone()
    
    # Get recent heals
    recent_query = text("""
        SELECT 
            shl.field_name,
            shl.old_selector,
            shl.new_selector,
            shl.confidence,
            shl.status,
            shl.healed_at,
            s.name as source_name
        FROM selector_heal_log shl
        JOIN sources s ON shl.source_id = s.id
        ORDER BY shl.healed_at DESC
        LIMIT 20
    """)
    recent = db.execute(recent_query).fetchall()
    
    return {
        "total_attempts": stats.total or 0,
        "resolved": stats.resolved or 0,
        "pending": stats.pending or 0,
        "success_rate": float(stats.success_rate or 0),
        "avg_confidence": float(stats.avg_confidence or 0),
        "recent_heals": [
            {
                "source_name": r.source_name,
                "field_name": r.field_name,
                "old_selector": r.old_selector,
                "new_selector": r.new_selector,
                "confidence": float(r.confidence) if r.confidence else 0,
                "status": r.status,
                "created_at": r.healed_at.isoformat() if r.healed_at else None
            }
            for r in recent
        ]
    }

