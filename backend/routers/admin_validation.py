"""
Admin Validation routes.
Handles admin-only operations for result validation (inline edit, approve, reject, send to validated).
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from pydantic import BaseModel, Field, validator
from decimal import Decimal

from dependencies import get_db, require_admin
from models import User, CleanedResult, ValidatedResult

router = APIRouter()


# Request schemas
class InlineEditRequest(BaseModel):
    """Request schema for inline editing a single field"""
    field_name: str = Field(..., description="Name of the field to edit")
    field_value: Optional[str] = Field(None, description="New value for the field (can be null)")
    temporary: bool = Field(False, description="If true, store in user_overrides; if false, update main column")
    
    @validator('field_name')
    def validate_field_name(cls, v):
        """Allow editing ALL fields (no restrictions for Feature 2)"""
        # All fields are now editable
        return v


class ApproveRequest(BaseModel):
    """Request schema for approving a result"""
    notes: Optional[str] = Field(None, description="Optional notes about the approval")


class RejectRequest(BaseModel):
    """Request schema for rejecting a result"""
    notes: Optional[str] = Field(None, description="Optional notes about the rejection")


class SendToValidatedRequest(BaseModel):
    """Request schema for sending approved result to validated_results table"""
    notes: Optional[str] = Field(None, description="Optional notes about the validation")


# Response schemas
class InlineEditResponse(BaseModel):
    """Response schema for inline edit"""
    id: str
    field_name: str
    field_value: Optional[str]
    is_edited: bool
    is_temporary: bool
    message: str


class ApproveResponse(BaseModel):
    """Response schema for approve action"""
    id: str
    status: str
    message: str


class RejectResponse(BaseModel):
    """Response schema for reject action"""
    id: str
    status: str
    message: str


class SendToValidatedResponse(BaseModel):
    """Response schema for send to validated action"""
    cleaned_result_id: str
    validated_result_id: str
    message: str


@router.patch("/results/{result_id}", response_model=InlineEditResponse)
def inline_edit_result(
    result_id: str,
    edit_request: InlineEditRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Inline edit a single field in a cleaned result.
    
    Feature 2: Full Inline Edit
    - All fields are now editable (no restrictions)
    - Supports temporary vs permanent edits
    - Temporary edits stored in user_overrides JSONB column
    - Permanent edits update main column and set is_edited=True
    - Protected by require_admin dependency
    """
    from datetime import datetime
    
    # Find the result
    result = db.query(CleanedResult).filter(CleanedResult.id == result_id).first()
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Result not found"
        )
    
    field_name = edit_request.field_name
    field_value = edit_request.field_value
    is_temporary = edit_request.temporary
    
    # Validate and convert field value based on field type
    try:
        # Numeric fields
        if field_name in ['rating_overall', 'rating_cleanliness', 'rating_location',
                         'rating_facilities', 'rating_service', 'rating_value']:
            if field_value is not None:
                rating = float(field_value)
                if rating < 0 or rating > 10:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Rating must be between 0 and 10"
                    )
                field_value = Decimal(str(rating)) if not is_temporary else field_value
            else:
                field_value = None
        
        elif field_name in ['price_min', 'price_max']:
            if field_value is not None:
                price = float(field_value)
                if price < 0:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Price must be a positive number"
                    )
                field_value = Decimal(str(price)) if not is_temporary else field_value
            else:
                field_value = None
        
        elif field_name in ['latitude', 'longitude']:
            if field_value is not None:
                coord = float(field_value)
                if field_name == 'latitude' and (coord < -90 or coord > 90):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Latitude must be between -90 and 90"
                    )
                if field_name == 'longitude' and (coord < -180 or coord > 180):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Longitude must be between -180 and 180"
                    )
                field_value = Decimal(str(coord)) if not is_temporary else field_value
            else:
                field_value = None
        
        elif field_name in ['star_rating', 'review_count', 'image_count', 'established_year']:
            if field_value is not None:
                field_value = int(field_value) if not is_temporary else field_value
            else:
                field_value = None
        
        # Boolean fields
        elif field_name in ['pets_allowed', 'breakfast_available', 'includes_breakfast',
                           'includes_taxes', 'free_cancellation', 'is_edited', 'is_duplicate']:
            if field_value is not None:
                field_value = field_value.lower() in ['true', '1', 'yes'] if not is_temporary else field_value
            else:
                field_value = None
        
        # String fields - keep as is
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid value for field '{field_name}': {str(e)}"
        )
    
    if is_temporary:
        # Store in user_overrides JSONB column
        # Must copy the dict and use flag_modified so SQLAlchemy detects the JSONB mutation
        overrides = dict(result.user_overrides or {})
        overrides[field_name] = {
            "value": field_value,
            "temp": True,
            "edited_by": current_user.id,
            "edited_at": datetime.utcnow().isoformat()
        }
        result.user_overrides = overrides
        flag_modified(result, "user_overrides")
    else:
        # Permanent: update main column and remove any temp override for this field
        if hasattr(result, field_name):
            setattr(result, field_name, field_value)
            result.is_edited = True
            result.updated_at = datetime.utcnow()
            # Clean up any temporary override for this field
            if result.user_overrides and field_name in result.user_overrides:
                overrides = dict(result.user_overrides)
                del overrides[field_name]
                result.user_overrides = overrides
                flag_modified(result, "user_overrides")
        else:
            # Permanent for a custom column: store in user_overrides with a special flag
            # Custom columns don't exist on the model, so we store them persistently in user_overrides
            overrides = dict(result.user_overrides or {})
            overrides[field_name] = {
                "value": field_value,
                "temp": False,
                "custom": True,
                "edited_by": current_user.id,
                "edited_at": datetime.utcnow().isoformat()
            }
            result.user_overrides = overrides
            flag_modified(result, "user_overrides")
            result.is_edited = True
    
    db.commit()
    db.refresh(result)
    
    # Convert back to string for response
    response_value = str(field_value) if field_value is not None else None
    
    return {
        "id": str(result.id),
        "field_name": field_name,
        "field_value": response_value,
        "is_edited": result.is_edited,
        "is_temporary": is_temporary,
        "message": f"Field '{field_name}' {'temporarily ' if is_temporary else ''}updated successfully"
    }


@router.post("/results/{result_id}/approve", response_model=ApproveResponse)
def approve_result(
    result_id: str,
    approve_request: ApproveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Approve a cleaned result.
    
    - Protected by require_admin dependency
    - Updates cleaned_results.status to APPROVED
    - Does NOT insert into validated_results (that's done by send_to_validated endpoint)
    - Returns updated status
    """
    # Find the result
    result = db.query(CleanedResult).filter(CleanedResult.id == result_id).first()
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Result not found"
        )
    
    # Check if already approved
    if result.status == "APPROVED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Result is already approved"
        )
    
    # Update status to APPROVED
    result.status = "APPROVED"
    
    db.commit()
    db.refresh(result)
    
    return {
        "id": str(result.id),
        "status": result.status,
        "message": "Result approved successfully"
    }


@router.post("/results/{result_id}/reject", response_model=RejectResponse)
def reject_result(
    result_id: str,
    reject_request: RejectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Reject a cleaned result.
    
    - Protected by require_admin dependency
    - Updates cleaned_results.status to REJECTED
    - Returns updated status
    """
    # Find the result
    result = db.query(CleanedResult).filter(CleanedResult.id == result_id).first()
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Result not found"
        )
    
    # Check if already rejected
    if result.status == "REJECTED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Result is already rejected"
        )
    
    # Update status to REJECTED
    result.status = "REJECTED"
    
    db.commit()
    db.refresh(result)
    
    return {
        "id": str(result.id),
        "status": result.status,
        "message": "Result rejected successfully"
    }


@router.post("/results/{result_id}/send-to-validated", response_model=SendToValidatedResponse)
def send_to_validated(
    result_id: str,
    send_request: SendToValidatedRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Send an APPROVED cleaned result to validated_results table.
    
    - Protected by require_admin dependency
    - Only works for results with status=APPROVED
    - Creates a record in validated_results table
    - Copies job_id, source_id, category_id from cleaned_result
    - Sets validated_by to current admin user
    - Returns validated_result ID
    """
    # Find the result
    result = db.query(CleanedResult).filter(CleanedResult.id == result_id).first()
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Result not found"
        )
    
    # Check if status is APPROVED
    if result.status != "APPROVED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only APPROVED results can be sent to validated_results. Current status: " + result.status
        )
    
    # Check if already in validated_results
    existing = db.query(ValidatedResult).filter(
        ValidatedResult.cleaned_result_id == result.id
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Result has already been sent to validated_results"
        )
    
    # Create validated_result record
    validated_result = ValidatedResult(
        cleaned_result_id=result.id,
        job_id=result.job_id,
        source_id=result.source_id,
        category_id=result.category_id,
        validated_by=current_user.id,
        notes=send_request.notes
    )
    
    db.add(validated_result)
    db.commit()
    db.refresh(validated_result)
    
    return {
        "cleaned_result_id": str(result.id),
        "validated_result_id": str(validated_result.id),
        "message": "Result sent to validated_results successfully"
    }
