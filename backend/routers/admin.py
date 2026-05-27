"""
Admin routes.
Handles admin-only operations like viewing all results with filtering and sorting.
"""
from typing import List, Optional
from datetime import datetime
import csv
import json
from io import StringIO, BytesIO
from fastapi import APIRouter, Depends, Query, HTTPException, status
import openpyxl
from openpyxl.styles import Font, PatternFill
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict

from dependencies import get_db, require_admin
from models import User, CleanedResult
from models.column_definition import ColumnDefinition
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
    status: str
    scraper_source: Optional[str] = None
    merged_from_sources: Optional[List[int]] = None
    thumbnail_url: Optional[str] = None
    image_urls: Optional[list] = None
    amenities: Optional[list] = None
    opening_hours: Optional[str] = None
    checkin_time: Optional[str] = None
    checkout_time: Optional[str] = None
    # Go scraper rich fields from extra_data
    place_id: Optional[str] = None
    data_id: Optional[str] = None
    cid: Optional[str] = None
    plus_code: Optional[str] = None
    timezone: Optional[str] = None
    business_status: Optional[str] = None
    images_count: Optional[int] = None
    reservations_link: Optional[str] = None
    order_link: Optional[str] = None
    menu_link: Optional[str] = None
    owner_name: Optional[str] = None
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
    format: str = Query("csv", description="Export format: csv, json, or excel"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status (PENDING, APPROVED, REJECTED)"),
    category_id: Optional[int] = Query(None, description="Filter by category ID"),
    city: Optional[str] = Query(None, description="Filter by city name"),
    source_id: Optional[int] = Query(None, description="Filter by source ID"),
    scraper_source: Optional[str] = Query(None, description="Filter by scraper source (go_scraper, playwright, serpapi)"),
    is_duplicate: Optional[bool] = Query(None, description="Filter by duplicate status"),
    min_completeness: Optional[float] = Query(None, ge=0, le=100, description="Minimum data completeness percentage"),
    has_phone: Optional[bool] = Query(None, description="Filter by phone presence"),
    has_website: Optional[bool] = Query(None, description="Filter by website presence"),
    has_rating: Optional[bool] = Query(None, description="Filter by rating presence"),
    has_opening_hours: Optional[bool] = Query(None, description="Filter by opening hours presence"),
    created_after: Optional[str] = Query(None, description="Filter by created date (ISO format)"),
    created_before: Optional[str] = Query(None, description="Filter by created date (ISO format)"),
    sort_by: str = Query("created_at", description="Sort by field (data_completeness or created_at)"),
    columns: Optional[str] = Query(None, description="Comma-separated list of columns to include in export"),
    labels: Optional[str] = Query(None, description="Column renames in format: name:New Name,city:Location"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Export filtered admin results as CSV, JSON, or Excel.
    
    - Protected by require_admin dependency
    - Accepts same filters as GET /results/
    - format: 'csv', 'json', or 'excel'
    - Maximum 10,000 results per export
    - Returns file download with appropriate Content-Type and Content-Disposition headers
    """
    # Validate format
    if format not in ["csv", "json", "excel"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid format. Must be 'csv', 'json', or 'excel'"
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
    
    # New filters
    if source_id is not None:
        query = query.filter(CleanedResult.source_id == source_id)
    
    if scraper_source is not None:
        query = query.filter(CleanedResult.scraper_source == scraper_source)
    
    if is_duplicate is not None:
        query = query.filter(CleanedResult.is_duplicate == is_duplicate)
    
    if min_completeness is not None:
        query = query.filter(CleanedResult.data_completeness >= min_completeness)
    
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
    
    if has_opening_hours is not None:
        if has_opening_hours:
            # Filter for records with non-empty opening hours (exclude NULL, '', '{}', 'Working Hours')
            from sqlalchemy import and_
            query = query.filter(and_(
                CleanedResult.opening_hours.isnot(None),
                CleanedResult.opening_hours != '',
                CleanedResult.opening_hours != '{}',
                CleanedResult.opening_hours != 'Working Hours'
            ))
        else:
            # Filter for records without meaningful opening hours
            from sqlalchemy import or_
            query = query.filter(or_(
                CleanedResult.opening_hours.is_(None),
                CleanedResult.opening_hours == '',
                CleanedResult.opening_hours == '{}',
                CleanedResult.opening_hours == 'Working Hours'
            ))
    
    if created_after:
        try:
            date_after = datetime.fromisoformat(created_after)
            query = query.filter(CleanedResult.created_at >= date_after)
        except ValueError:
            pass
    
    if created_before:
        try:
            date_before = datetime.fromisoformat(created_before)
            query = query.filter(CleanedResult.created_at <= date_before)
        except ValueError:
            pass
    
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
    
    # Parse selected columns (if provided)
    selected_cols = [c.strip() for c in columns.split(',')] if columns else None
    
    # Parse labels parameter: "name:New Name,city:City Name"
    label_map = {}
    if labels:
        for pair in labels.split(','):
            if ':' in pair:
                key, label = pair.split(':', 1)
                label_map[key.strip()] = label.strip()
    
    if format == "csv":
        return export_as_csv(results, timestamp, selected_cols, label_map)
    elif format == "excel":
        return export_as_excel(results, timestamp, selected_cols, label_map)
    else:  # json
        return export_as_json(results, timestamp, total, selected_cols, label_map)


def _apply_user_overrides(result: CleanedResult) -> dict:
    """
    Return a dict of field values with user_overrides merged on top.
    - Temporary overrides: included in exports for the current session only
    - Custom column overrides (temp=False, custom=True): always included
    """
    overrides = result.user_overrides or {}
    fields = {
        "name": result.name,
        "city": result.city,
        "address": result.address,
        "latitude": result.latitude,
        "longitude": result.longitude,
        "phone_primary": result.phone_primary,
        "phone_secondary": result.phone_secondary,
        "email": result.email,
        "website": result.website,
        "description_short": result.description_short,
        "rating_overall": result.rating_overall,
        "review_count": result.review_count,
        "price_min": result.price_min,
        "price_max": result.price_max,
        "currency": result.currency,
        "thumbnail_url": result.thumbnail_url,
        "opening_hours": result.opening_hours,
        "checkin_time": result.checkin_time,
        "checkout_time": result.checkout_time,
    }
    # Apply overrides (both temporary session edits and permanent custom columns)
    for field, override in overrides.items():
        if isinstance(override, dict) and "value" in override:
            fields[field] = override["value"]  # includes custom columns too
    return fields


def export_as_csv(results: List[CleanedResult], timestamp: str, selected_cols=None, label_map=None) -> StreamingResponse:
    """
    Generate CSV export with headers and formatted data.
    Temporary user_overrides are merged so the export matches what the admin sees.
    Only includes columns in selected_cols (if provided).
    Uses label_map for column renames (FIX 2).
    """
    label_map = label_map or {}
    
    # Full column map: key → (header label, value extractor)
    ALL_COLUMNS = [
        ("id",               "ID",                   lambda r, f: str(r.id)),
        ("job_id",           "Job ID",               lambda r, f: str(r.job_id)),
        ("source_id",        "Source ID",            lambda r, f: r.source_id),
        ("source_name",      "Source Name",          lambda r, f: getattr(r, 'source_name', '') or ''),
        ("category_id",      "Category ID",          lambda r, f: r.category_id),
        ("name",             "Name",                 lambda r, f: f.get("name") or ""),
        ("city",             "City",                 lambda r, f: f.get("city") or ""),
        ("address",          "Address",              lambda r, f: f.get("address") or ""),
        ("latitude",         "Latitude",             lambda r, f: float(f.get("latitude")) if f.get("latitude") else ""),
        ("longitude",        "Longitude",            lambda r, f: float(f.get("longitude")) if f.get("longitude") else ""),
        ("phone_primary",    "Phone Primary",        lambda r, f: f.get("phone_primary") or ""),
        ("phone_secondary",  "Phone Secondary",      lambda r, f: f.get("phone_secondary") or ""),
        ("email",            "Email",                lambda r, f: f.get("email") or ""),
        ("website",          "Website",              lambda r, f: f.get("website") or ""),
        ("description_short","Description",          lambda r, f: f.get("description_short") or ""),
        ("rating_overall",   "Rating",               lambda r, f: float(f.get("rating_overall")) if f.get("rating_overall") else ""),
        ("review_count",     "Review Count",         lambda r, f: f.get("review_count") or ""),
        ("price_min",        "Price Min",            lambda r, f: float(f.get("price_min")) if f.get("price_min") else ""),
        ("price_max",        "Price Max",            lambda r, f: float(f.get("price_max")) if f.get("price_max") else ""),
        ("currency",         "Currency",             lambda r, f: f.get("currency") or ""),
        ("thumbnail_url",    "Thumbnail URL",        lambda r, f: f.get("thumbnail_url") or ""),
        ("image_urls",       "Image URLs",           lambda r, f: json.dumps(r.image_urls) if r.image_urls else ""),
        ("amenities",        "Amenities",            lambda r, f: json.dumps(r.amenities) if r.amenities else ""),
        ("opening_hours",    "Opening Hours",        lambda r, f: f.get("opening_hours") or ""),
        ("checkin_time",     "Checkin Time",         lambda r, f: f.get("checkin_time") or ""),
        ("checkout_time",    "Checkout Time",        lambda r, f: f.get("checkout_time") or ""),
        ("scraper_source",   "Scraper Source",       lambda r, f: r.scraper_source or ""),
        ("data_completeness","Data Completeness (%)",lambda r, f: float(r.data_completeness) if r.data_completeness else ""),
        ("status",           "Status",               lambda r, f: r.status),
        ("created_at",       "Created At",           lambda r, f: r.created_at.isoformat() if r.created_at else ""),
    ]

    # Add custom columns dynamically from selected_cols
    if selected_cols:
        # Find custom columns (those starting with "custom_")
        custom_col_keys = [col for col in selected_cols if col.startswith("custom_")]
        for custom_key in custom_col_keys:
            # Generate a nice label from the key (e.g., "custom_test_col" -> "Test Col")
            label = custom_key.replace("custom_", "").replace("_", " ").title()
            ALL_COLUMNS.append((
                custom_key,
                label,
                lambda r, f, key=custom_key: f.get(key) or ""
            ))

    # Filter to selected columns (or use all if none specified)
    cols = [(k, h, fn) for k, h, fn in ALL_COLUMNS if selected_cols is None or k in selected_cols]
    # Preserve user-selected order
    if selected_cols:
        col_map = {k: (k, h, fn) for k, h, fn in cols}
        cols = [col_map[k] for k in selected_cols if k in col_map]
    
    # Apply label renames (FIX 2)
    cols = [(k, label_map.get(k, h), fn) for k, h, fn in cols]

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow([h for _, h, _ in cols])

    for result in results:
        f = _apply_user_overrides(result)
        writer.writerow([fn(result, f) for _, _, fn in cols])

    csv_content = output.getvalue()
    output.close()

    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=results_{timestamp}.csv"}
    )
def export_as_excel(results: List[CleanedResult], timestamp: str, selected_cols=None, label_map=None) -> StreamingResponse:
    """
    Generate Excel export with formatted headers and data.
    Temporary user_overrides are merged so the export matches what the admin sees.
    Only includes columns in selected_cols (if provided).
    """
    ALL_COLUMNS = [
        ("id",               "ID",                   lambda r, f: str(r.id)),
        ("job_id",           "Job ID",               lambda r, f: str(r.job_id)),
        ("source_id",        "Source ID",            lambda r, f: r.source_id),
        ("source_name",      "Source Name",          lambda r, f: getattr(r, 'source_name', '') or ''),
        ("category_id",      "Category ID",          lambda r, f: r.category_id),
        ("name",             "Name",                 lambda r, f: f.get("name") or ""),
        ("city",             "City",                 lambda r, f: f.get("city") or ""),
        ("address",          "Address",              lambda r, f: f.get("address") or ""),
        ("latitude",         "Latitude",             lambda r, f: float(f.get("latitude")) if f.get("latitude") else None),
        ("longitude",        "Longitude",            lambda r, f: float(f.get("longitude")) if f.get("longitude") else None),
        ("phone_primary",    "Phone Primary",        lambda r, f: f.get("phone_primary") or ""),
        ("phone_secondary",  "Phone Secondary",      lambda r, f: f.get("phone_secondary") or ""),
        ("email",            "Email",                lambda r, f: f.get("email") or ""),
        ("website",          "Website",              lambda r, f: f.get("website") or ""),
        ("description_short","Description",          lambda r, f: f.get("description_short") or ""),
        ("rating_overall",   "Rating",               lambda r, f: float(f.get("rating_overall")) if f.get("rating_overall") else None),
        ("review_count",     "Review Count",         lambda r, f: f.get("review_count") or None),
        ("price_min",        "Price Min",            lambda r, f: float(f.get("price_min")) if f.get("price_min") else None),
        ("price_max",        "Price Max",            lambda r, f: float(f.get("price_max")) if f.get("price_max") else None),
        ("currency",         "Currency",             lambda r, f: f.get("currency") or ""),
        ("thumbnail_url",    "Thumbnail URL",        lambda r, f: f.get("thumbnail_url") or ""),
        ("image_urls",       "Image URLs",           lambda r, f: json.dumps(r.image_urls) if r.image_urls else ""),
        ("amenities",        "Amenities",            lambda r, f: json.dumps(r.amenities) if r.amenities else ""),
        ("opening_hours",    "Opening Hours",        lambda r, f: f.get("opening_hours") or ""),
        ("checkin_time",     "Checkin Time",         lambda r, f: f.get("checkin_time") or ""),
        ("checkout_time",    "Checkout Time",        lambda r, f: f.get("checkout_time") or ""),
        ("scraper_source",   "Scraper Source",       lambda r, f: r.scraper_source or ""),
        ("data_completeness","Data Completeness (%)",lambda r, f: float(r.data_completeness) if r.data_completeness else None),
        ("status",           "Status",               lambda r, f: r.status),
        ("created_at",       "Created At",           lambda r, f: r.created_at.isoformat() if r.created_at else ""),
    ]

    # Add custom columns dynamically from selected_cols
    if selected_cols:
        custom_col_keys = [col for col in selected_cols if col.startswith("custom_")]
        for custom_key in custom_col_keys:
            label = custom_key.replace("custom_", "").replace("_", " ").title()
            ALL_COLUMNS.append((
                custom_key,
                label,
                lambda r, f, key=custom_key: f.get(key) or ""
            ))

    cols = [(k, h, fn) for k, h, fn in ALL_COLUMNS if selected_cols is None or k in selected_cols]
    if selected_cols:
        col_map = {k: (k, h, fn) for k, h, fn in cols}
        cols = [col_map[k] for k in selected_cols if k in col_map]
    
    # Apply label renames (FIX 2)
    label_map = label_map or {}
    cols = [(k, label_map.get(k, h), fn) for k, h, fn in cols]

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Nepal Business Data"

    ws.append([h for _, h, _ in cols])

    header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF")
    for cell in ws[1]:
        cell.font = header_font
        cell.fill = header_fill

    for result in results:
        f = _apply_user_overrides(result)
        ws.append([fn(result, f) for _, _, fn in cols])

    for column in ws.columns:
        max_length = 0
        column_letter = column[0].column_letter
        for cell in column:
            try:
                if cell.value:
                    max_length = max(max_length, len(str(cell.value)))
            except:
                pass
        ws.column_dimensions[column_letter].width = min(max_length + 2, 50)

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=nepal_business_data_{timestamp}.xlsx"}
    )


def export_as_json(results: List[CleanedResult], timestamp: str, total: int, selected_cols=None, label_map=None) -> StreamingResponse:
    """
    Generate JSON export with metadata and full results array.
    Only includes keys in selected_cols (if provided).
    """
    geocoded_count = sum(1 for r in results if r.latitude is not None and r.longitude is not None)
    geocoding_success_rate = (geocoded_count / total * 100) if total > 0 else 0

    data = {
        "metadata": {
            "exported_at": datetime.utcnow().isoformat(),
            "total_count": total,
            "geocoded_count": geocoded_count,
            "geocoding_success_rate": f"{geocoding_success_rate:.1f}%",
            "format": "json",
            "columns": selected_cols or "all"
        },
        "results": []
    }

    # Full field map: key → value extractor
    ALL_FIELDS = {
        "id":               lambda r, f: str(r.id),
        "job_id":           lambda r, f: str(r.job_id),
        "source_id":        lambda r, f: r.source_id,
        "source_name":      lambda r, f: getattr(r, 'source_name', None),
        "category_id":      lambda r, f: r.category_id,
        "name":             lambda r, f: f.get("name"),
        "city":             lambda r, f: f.get("city"),
        "address":          lambda r, f: f.get("address"),
        "latitude":         lambda r, f: float(f.get("latitude")) if f.get("latitude") else None,
        "longitude":        lambda r, f: float(f.get("longitude")) if f.get("longitude") else None,
        "phone_primary":    lambda r, f: f.get("phone_primary"),
        "phone_secondary":  lambda r, f: f.get("phone_secondary"),
        "email":            lambda r, f: f.get("email"),
        "website":          lambda r, f: f.get("website"),
        "description_short":lambda r, f: f.get("description_short"),
        "rating_overall":   lambda r, f: float(f.get("rating_overall")) if f.get("rating_overall") else None,
        "review_count":     lambda r, f: f.get("review_count"),
        "price_min":        lambda r, f: float(f.get("price_min")) if f.get("price_min") else None,
        "price_max":        lambda r, f: float(f.get("price_max")) if f.get("price_max") else None,
        "currency":         lambda r, f: f.get("currency"),
        "thumbnail_url":    lambda r, f: f.get("thumbnail_url"),
        "image_urls":       lambda r, f: r.image_urls or [],
        "amenities":        lambda r, f: r.amenities or [],
        "opening_hours":    lambda r, f: f.get("opening_hours"),
        "checkin_time":     lambda r, f: f.get("checkin_time"),
        "checkout_time":    lambda r, f: f.get("checkout_time"),
        "scraper_source":   lambda r, f: r.scraper_source,
        "data_completeness":lambda r, f: float(r.data_completeness) if r.data_completeness else None,
        "status":           lambda r, f: r.status,
        "created_at":       lambda r, f: r.created_at.isoformat() if r.created_at else None,
    }

    # Add custom columns dynamically from selected_cols
    if selected_cols:
        custom_col_keys = [col for col in selected_cols if col.startswith("custom_")]
        for custom_key in custom_col_keys:
            ALL_FIELDS[custom_key] = lambda r, f, key=custom_key: f.get(key)

    # Determine which fields to include
    fields_to_include = selected_cols if selected_cols else list(ALL_FIELDS.keys())

    for result in results:
        f = _apply_user_overrides(result)
        row = {}
        for key in fields_to_include:
            if key in ALL_FIELDS:
                row[key] = ALL_FIELDS[key](result, f)
        data["results"].append(row)

    json_content = json.dumps(data, indent=2)

    return StreamingResponse(
        iter([json_content]),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename=results_{timestamp}.json"}
    )


@router.get("/results/", response_model=PaginatedAdminResultsResponse)
def get_admin_results(
    status: Optional[str] = Query(None, description="Filter by status (PENDING, APPROVED, REJECTED)"),
    category_id: Optional[int] = Query(None, description="Filter by category ID"),
    city: Optional[str] = Query(None, description="Filter by city name"),
    source_id: Optional[int] = Query(None, description="Filter by source ID"),
    scraper_source: Optional[str] = Query(None, description="Filter by scraper source (go_scraper, playwright, serpapi)"),
    is_duplicate: Optional[bool] = Query(None, description="Filter by duplicate status (true=duplicates only, false=unique only)"),
    min_completeness: Optional[float] = Query(None, ge=0, le=100, description="Minimum data completeness percentage"),
    has_phone: Optional[bool] = Query(None, description="Filter by phone presence (true=has phone, false=no phone)"),
    has_website: Optional[bool] = Query(None, description="Filter by website presence (true=has website, false=no website)"),
    has_rating: Optional[bool] = Query(None, description="Filter by rating presence (true=has rating, false=no rating)"),
    has_opening_hours: Optional[bool] = Query(None, description="Filter by opening hours presence"),
    created_after: Optional[str] = Query(None, description="Filter by created date (ISO format: YYYY-MM-DD)"),
    created_before: Optional[str] = Query(None, description="Filter by created date (ISO format: YYYY-MM-DD)"),
    sort_by: str = Query("created_at", description="Sort by field (data_completeness or created_at)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Page size (max 200)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Get paginated cleaned results for admin review.
    
    - Protected by require_admin dependency
    - Accepts query params: status, category_id, city, source_id, scraper_source, is_duplicate, min_completeness, 
      has_phone, has_website, has_rating, created_after, created_before, sort_by, page, page_size
    - sort_by can be 'data_completeness' or 'created_at'
    - Default page_size=50, max page_size=200
    - Returns paginated envelope with items, total, page, page_size, pages
    """
    # Build query
    query = db.query(CleanedResult)
    
    if category_id:
        query = query.filter(CleanedResult.category_id == category_id)
    
    if city:
        query = query.filter(CleanedResult.city.ilike(f"%{city}%"))
    
    # New filters
    if source_id is not None:
        query = query.filter(CleanedResult.source_id == source_id)
    
    if scraper_source is not None:
        query = query.filter(CleanedResult.scraper_source == scraper_source)
    
    if is_duplicate is not None:
        query = query.filter(CleanedResult.is_duplicate == is_duplicate)
    
    if min_completeness is not None:
        query = query.filter(CleanedResult.data_completeness >= min_completeness)
    
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
    
    if has_opening_hours is not None:
        if has_opening_hours:
            # Filter for records with non-empty opening hours (exclude NULL, '', '{}', 'Working Hours')
            from sqlalchemy import and_
            query = query.filter(and_(
                CleanedResult.opening_hours.isnot(None),
                CleanedResult.opening_hours != '',
                CleanedResult.opening_hours != '{}',
                CleanedResult.opening_hours != 'Working Hours'
            ))
        else:
            # Filter for records without meaningful opening hours
            from sqlalchemy import or_
            query = query.filter(or_(
                CleanedResult.opening_hours.is_(None),
                CleanedResult.opening_hours == '',
                CleanedResult.opening_hours == '{}',
                CleanedResult.opening_hours == 'Working Hours'
            ))
    
    if created_after:
        try:
            date_after = datetime.fromisoformat(created_after)
            query = query.filter(CleanedResult.created_at >= date_after)
        except ValueError:
            pass  # Ignore invalid date format
    
    if created_before:
        try:
            date_before = datetime.fromisoformat(created_before)
            query = query.filter(CleanedResult.created_at <= date_before)
        except ValueError:
            pass  # Ignore invalid date format
    
    # Apply sorting
    if sort_by == "data_completeness":
        query = query.order_by(CleanedResult.data_completeness.desc())
    else:  # default to created_at
        query = query.order_by(CleanedResult.created_at.desc())
    
    # Get total count
    total = query.count()
    
    # Get paginated results
    results = query.offset((page - 1) * page_size).limit(page_size).all()

    # Clear TEMPORARY user_overrides for results on this page.
    # Temporary edits are session-scoped: they show in the UI and export for
    # the current session, but are wiped the moment the data is re-fetched
    # (i.e. on page refresh). Custom column data (temp=False, custom=True) is preserved.
    from sqlalchemy.orm.attributes import flag_modified
    needs_commit = False
    for result in results:
        if result.user_overrides:
            # Keep only non-temporary overrides (custom columns)
            kept = {k: v for k, v in result.user_overrides.items()
                    if isinstance(v, dict) and not v.get("temp", False)}
            if kept != result.user_overrides:
                result.user_overrides = kept
                flag_modified(result, "user_overrides")
                needs_commit = True
    if needs_commit:
        db.commit()
    
    # Calculate total pages
    pages = -(-total // page_size) if total > 0 else 0  # Ceiling division

    # Build source name lookup for this page
    from models import Source
    source_ids = list({r.source_id for r in results})
    sources = db.query(Source).filter(Source.id.in_(source_ids)).all()
    source_name_map = {s.id: (s.display_name or s.name) for s in sources}
    
    # Convert to response format
    items = []
    for result in results:
        # Extract Go scraper rich fields from extra_data
        extra = result.extra_data or {}
        
        # Extract images from extra_data if available
        images_from_extra = []
        if extra.get('images'):
            images_from_extra = [img.get('link') for img in extra['images'] if isinstance(img, dict) and img.get('link')]
        
        # Get reservations, order, menu links
        reservations_link = None
        order_link = None
        menu_link = None
        
        if extra.get('reservations'):
            if isinstance(extra['reservations'], list) and len(extra['reservations']) > 0:
                reservations_link = extra['reservations'][0].get('link')
            elif isinstance(extra['reservations'], dict):
                reservations_link = extra['reservations'].get('link')
        
        if extra.get('order_online'):
            if isinstance(extra['order_online'], list) and len(extra['order_online']) > 0:
                order_link = extra['order_online'][0].get('link')
            elif isinstance(extra['order_online'], dict):
                order_link = extra['order_online'].get('link')
        
        if extra.get('menu'):
            if isinstance(extra['menu'], dict):
                menu_link = extra['menu'].get('link')
            elif isinstance(extra['menu'], str):
                menu_link = extra['menu']
        
        # Get owner name
        owner_name = None
        if extra.get('owner'):
            if isinstance(extra['owner'], dict):
                owner_name = extra['owner'].get('name')
            elif isinstance(extra['owner'], str):
                owner_name = extra['owner']
        
        items.append({
            "id": str(result.id),
            "job_id": str(result.job_id),
            "source_id": result.source_id,
            "source_name": source_name_map.get(result.source_id),
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
            "review_count": result.review_count,
            "price_min": float(result.price_min) if result.price_min else None,
            "price_max": float(result.price_max) if result.price_max else None,
            "currency": result.currency,
            "data_completeness": float(result.data_completeness) if result.data_completeness else None,
            "status": result.status,
            "scraper_source": result.scraper_source,
            "merged_from_sources": result.merged_from_sources if result.merged_from_sources else [],
            "thumbnail_url": result.thumbnail_url,
            "image_urls": images_from_extra if images_from_extra else (result.image_urls if result.image_urls else []),
            "amenities": result.amenities if result.amenities else [],
            "opening_hours": result.opening_hours,
            "checkin_time": result.checkin_time,
            "checkout_time": result.checkout_time,
            # Go scraper rich fields
            "place_id": extra.get('place_id'),
            "data_id": extra.get('data_id'),
            "cid": extra.get('cid'),
            "plus_code": extra.get('plus_code'),
            "timezone": extra.get('timezone'),
            "business_status": extra.get('business_status'),
            "images_count": len(images_from_extra) if images_from_extra else result.image_count,
            "reservations_link": reservations_link,
            "order_link": order_link,
            "menu_link": menu_link,
            "owner_name": owner_name,
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



# ═══════════════════════════════════════════════════════════════════════════════
# COLUMN DEFINITIONS ENDPOINTS (FIX 1)
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/column-definitions")
def get_column_definitions(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Get all custom column definitions.
    
    Returns list of column definitions with id, name, display_name, is_temporary.
    Protected by require_admin dependency.
    """
    cols = db.query(ColumnDefinition).order_by(ColumnDefinition.created_at).all()
    return [
        {
            "id": c.id,
            "name": c.name,
            "display_name": c.display_name,
            "is_temporary": c.is_temporary,
            "created_at": c.created_at.isoformat() if c.created_at else None
        }
        for c in cols
    ]


class CreateColumnDefinitionRequest(BaseModel):
    name: str
    display_name: str
    is_temporary: bool = False


@router.post("/column-definitions")
def create_column_definition(
    request: CreateColumnDefinitionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Create a new custom column definition.
    
    - name: Column key (e.g., "custom_verification_status")
    - display_name: Human-readable label (e.g., "Verification Status")
    - is_temporary: If True, column is session-scoped
    
    Protected by require_admin dependency.
    """
    # Check if column already exists
    existing = db.query(ColumnDefinition).filter(
        ColumnDefinition.name == request.name
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Column '{request.name}' already exists"
        )
    
    col = ColumnDefinition(
        name=request.name,
        display_name=request.display_name,
        is_temporary=request.is_temporary,
        created_by=current_user.id
    )
    db.add(col)
    db.commit()
    db.refresh(col)
    
    return {
        "id": col.id,
        "name": col.name,
        "display_name": col.display_name,
        "is_temporary": col.is_temporary
    }


@router.delete("/column-definitions/{col_id}")
def delete_column_definition(
    col_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Delete a custom column definition.
    
    Protected by require_admin dependency.
    """
    col = db.query(ColumnDefinition).filter(ColumnDefinition.id == col_id).first()
    
    if not col:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Column definition {col_id} not found"
        )
    
    db.delete(col)
    db.commit()
    
    return {"success": True, "message": f"Column '{col.name}' deleted"}


@router.put("/column-definitions/{col_id}")
def update_column_definition(
    col_id: int,
    display_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Update a column definition's display name (for permanent renames).
    
    Protected by require_admin dependency.
    """
    col = db.query(ColumnDefinition).filter(ColumnDefinition.id == col_id).first()
    
    if not col:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Column definition {col_id} not found"
        )
    
    col.display_name = display_name
    col.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(col)
    
    return {
        "id": col.id,
        "name": col.name,
        "display_name": col.display_name,
        "is_temporary": col.is_temporary
    }
