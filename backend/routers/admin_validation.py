"""
Admin Validation routes.
Handles admin-only operations for result validation (inline edit, approve, reject, send to validated).
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
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
    
    @validator('field_name')
    def validate_field_name(cls, v):
        """Only allow editing specific fields"""
        allowed_fields = [
            'name', 'city', 'address', 'rating_overall', 'price_min',
            'phone_primary', 'email', 'website', 'description_short'
        ]
        if v not in allowed_fields:
            raise ValueError(f"Field '{v}' is not editable. Allowed fields: {', '.join(allowed_fields)}")
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
    
    - Protected by require_admin dependency
    - Only allows editing specific fields (name, city, address, rating_overall, price_min, etc.)
    - Validates data types (rating 0-10, price positive number)
    - Sets is_edited flag to True
    - Returns updated field value
    """
    # Find the result
    result = db.query(CleanedResult).filter(CleanedResult.id == result_id).first()
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Result not found"
        )
    
    # Validate and convert field value based on field type
    field_name = edit_request.field_name
    field_value = edit_request.field_value
    
    try:
        if field_name == 'rating_overall':
            if field_value is not None:
                rating = float(field_value)
                if rating < 0 or rating > 10:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Rating must be between 0 and 10"
                    )
                field_value = Decimal(str(rating))
            else:
                field_value = None
        
        elif field_name == 'price_min':
            if field_value is not None:
                price = float(field_value)
                if price < 0:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Price must be a positive number"
                    )
                field_value = Decimal(str(price))
            else:
                field_value = None
        
        # For string fields, keep as is (or None)
        # field_value is already a string or None
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid value for field '{field_name}': {str(e)}"
        )
    
    # Update the field
    setattr(result, field_name, field_value)
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
        "message": f"Field '{field_name}' updated successfully"
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
