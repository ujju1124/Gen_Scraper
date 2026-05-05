# Feature 3: Result Validation Backend API Specification

**Date**: April 28, 2026  
**Status**: ✅ IMPLEMENTED  
**Router**: `backend/routers/admin_validation.py`  
**Prefix**: `/api/v1/admin`

---

## Overview

This document specifies the backend API endpoints for Feature 3: Result Validation in Admin Panel. All endpoints are protected by `require_admin` dependency and require admin authentication.

---

## Endpoints Summary

| Method | Endpoint | Purpose |
|--------|----------|---------|
| PATCH | `/api/v1/admin/results/{result_id}` | Inline edit a single field |
| POST | `/api/v1/admin/results/{result_id}/approve` | Approve a result (sets status=APPROVED) |
| POST | `/api/v1/admin/results/{result_id}/reject` | Reject a result (sets status=REJECTED) |
| POST | `/api/v1/admin/results/{result_id}/send-to-validated` | Send APPROVED result to validated_results table |

---

## 1. Inline Edit Result

### Endpoint
```
PATCH /api/v1/admin/results/{result_id}
```

### Purpose
Edit a single field in a cleaned result. This is used for inline editing in the admin table.

### Authentication
- Requires admin role
- Uses httpOnly cookie authentication

### Path Parameters
- `result_id` (string, UUID): ID of the cleaned result to edit

### Request Body
```json
{
  "field_name": "name",
  "field_value": "Updated Hotel Name"
}
```

**Schema:**
```typescript
{
  field_name: string;  // Required. Must be one of the allowed fields
  field_value: string | null;  // Optional. New value for the field (can be null)
}
```

**Allowed Fields:**
- `name` (string)
- `city` (string)
- `address` (string)
- `rating_overall` (number, 0-10)
- `price_min` (number, positive)
- `phone_primary` (string)
- `email` (string)
- `website` (string)
- `description_short` (string)

### Validation Rules
- **rating_overall**: Must be between 0 and 10
- **price_min**: Must be a positive number
- **field_name**: Must be one of the allowed fields
- **field_value**: Can be null to clear the field

### Response (200 OK)
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "field_name": "name",
  "field_value": "Updated Hotel Name",
  "is_edited": true,
  "message": "Field 'name' updated successfully"
}
```

**Schema:**
```typescript
{
  id: string;  // UUID of the cleaned result
  field_name: string;  // Name of the field that was edited
  field_value: string | null;  // New value of the field
  is_edited: boolean;  // Always true after edit
  message: string;  // Success message
}
```

### Error Responses

**404 Not Found** - Result not found
```json
{
  "detail": "Result not found"
}
```

**400 Bad Request** - Invalid field name
```json
{
  "detail": "Field 'invalid_field' is not editable. Allowed fields: name, city, address, rating_overall, price_min, phone_primary, email, website, description_short"
}
```

**400 Bad Request** - Invalid rating value
```json
{
  "detail": "Rating must be between 0 and 10"
}
```

**400 Bad Request** - Invalid price value
```json
{
  "detail": "Price must be a positive number"
}
```

### Behavior
- Sets `is_edited` flag to `True` on the cleaned result
- Updates only the specified field
- Validates data types based on field name
- Converts numeric strings to Decimal for rating and price fields

---

## 2. Approve Result

### Endpoint
```
POST /api/v1/admin/results/{result_id}/approve
```

### Purpose
Approve a cleaned result by setting its status to APPROVED. This does NOT insert into validated_results table (that's done by the send-to-validated endpoint).

### Authentication
- Requires admin role
- Uses httpOnly cookie authentication

### Path Parameters
- `result_id` (string, UUID): ID of the cleaned result to approve

### Request Body
```json
{
  "notes": "Looks good, approved for validation"
}
```

**Schema:**
```typescript
{
  notes?: string;  // Optional notes about the approval
}
```

### Response (200 OK)
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "APPROVED",
  "message": "Result approved successfully"
}
```

**Schema:**
```typescript
{
  id: string;  // UUID of the cleaned result
  status: string;  // New status (always "APPROVED")
  message: string;  // Success message
}
```

### Error Responses

**404 Not Found** - Result not found
```json
{
  "detail": "Result not found"
}
```

**400 Bad Request** - Already approved
```json
{
  "detail": "Result is already approved"
}
```

### Behavior
- Updates `cleaned_results.status` to `APPROVED`
- Does NOT create a record in `validated_results` table
- Can be called on results with status PENDING or REJECTED
- Cannot be called on already APPROVED results

---

## 3. Reject Result

### Endpoint
```
POST /api/v1/admin/results/{result_id}/reject
```

### Purpose
Reject a cleaned result by setting its status to REJECTED.

### Authentication
- Requires admin role
- Uses httpOnly cookie authentication

### Path Parameters
- `result_id` (string, UUID): ID of the cleaned result to reject

### Request Body
```json
{
  "notes": "Duplicate entry, rejecting"
}
```

**Schema:**
```typescript
{
  notes?: string;  // Optional notes about the rejection
}
```

### Response (200 OK)
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "REJECTED",
  "message": "Result rejected successfully"
}
```

**Schema:**
```typescript
{
  id: string;  // UUID of the cleaned result
  status: string;  // New status (always "REJECTED")
  message: string;  // Success message
}
```

### Error Responses

**404 Not Found** - Result not found
```json
{
  "detail": "Result not found"
}
```

**400 Bad Request** - Already rejected
```json
{
  "detail": "Result is already rejected"
}
```

### Behavior
- Updates `cleaned_results.status` to `REJECTED`
- Can be called on results with status PENDING or APPROVED
- Cannot be called on already REJECTED results

---

## 4. Send to Validated

### Endpoint
```
POST /api/v1/admin/results/{result_id}/send-to-validated
```

### Purpose
Send an APPROVED cleaned result to the validated_results table. This is the final step after approval.

### Authentication
- Requires admin role
- Uses httpOnly cookie authentication

### Path Parameters
- `result_id` (string, UUID): ID of the cleaned result to send to validated

### Request Body
```json
{
  "notes": "Final validation complete, sending to production"
}
```

**Schema:**
```typescript
{
  notes?: string;  // Optional notes about the validation
}
```

### Response (200 OK)
```json
{
  "cleaned_result_id": "550e8400-e29b-41d4-a716-446655440000",
  "validated_result_id": "660e8400-e29b-41d4-a716-446655440001",
  "message": "Result sent to validated_results successfully"
}
```

**Schema:**
```typescript
{
  cleaned_result_id: string;  // UUID of the cleaned result
  validated_result_id: string;  // UUID of the newly created validated result
  message: string;  // Success message
}
```

### Error Responses

**404 Not Found** - Result not found
```json
{
  "detail": "Result not found"
}
```

**400 Bad Request** - Not approved
```json
{
  "detail": "Only APPROVED results can be sent to validated_results. Current status: PENDING"
}
```

**400 Bad Request** - Already sent
```json
{
  "detail": "Result has already been sent to validated_results"
}
```

### Behavior
- Only works for results with `status = APPROVED`
- Creates a new record in `validated_results` table with:
  - `cleaned_result_id`: ID of the cleaned result
  - `job_id`: Copied from cleaned result
  - `source_id`: Copied from cleaned result
  - `category_id`: Copied from cleaned result
  - `validated_by`: Current admin user ID
  - `validated_at`: Current timestamp (auto-set)
  - `notes`: Optional notes from request
- Prevents duplicate sends (unique constraint on cleaned_result_id)

---

## Database Schema Changes

### Migration: 0002_extend_validated_results_table.py

**Changes to `validated_results` table:**

1. **Renamed Columns:**
   - `pushed_at` → `validated_at`
   - `pushed_by` → `validated_by`

2. **New Columns:**
   - `job_id` (UUID, nullable, FK to scrape_jobs.id)
   - `source_id` (INTEGER, nullable, FK to sources.id)
   - `category_id` (INTEGER, nullable, FK to categories.id)

3. **New Indexes:**
   - `idx_validated_results_job_id` on `job_id`
   - `idx_validated_results_category_id` on `category_id`
   - `idx_validated_results_validated_at` on `validated_at`
   - `idx_validated_results_validated_by` on `validated_by`

### Updated ValidatedResult Model

```python
class ValidatedResult(Base):
    __tablename__ = "validated_results"
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    cleaned_result_id = Column(UUID(as_uuid=True), ForeignKey("cleaned_results.id"), nullable=False, unique=True)
    job_id = Column(UUID(as_uuid=True), ForeignKey("scrape_jobs.id"), nullable=True, index=True)
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True, index=True)
    validated_by = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    validated_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    notes = Column(Text, nullable=True)
```

---

## Workflow

### Typical Admin Workflow

1. **View Results**: Admin views results via `GET /api/v1/admin/results/`
2. **Inline Edit** (optional): Admin edits fields via `PATCH /api/v1/admin/results/{id}`
3. **Approve**: Admin approves result via `POST /api/v1/admin/results/{id}/approve`
4. **Send to Validated**: Admin sends approved result via `POST /api/v1/admin/results/{id}/send-to-validated`

### Alternative: Reject Workflow

1. **View Results**: Admin views results via `GET /api/v1/admin/results/`
2. **Reject**: Admin rejects result via `POST /api/v1/admin/results/{id}/reject`

### Status Transitions

```
PENDING → APPROVED → (sent to validated_results)
PENDING → REJECTED
APPROVED → REJECTED (if admin changes mind)
REJECTED → APPROVED (if admin changes mind)
```

---

## Security

### Authentication
- All endpoints require admin role
- Uses `require_admin` dependency
- Validates httpOnly cookie authentication

### Authorization
- Only users with `role = "admin"` can access these endpoints
- Regular users get 403 Forbidden

### Data Validation
- Field names validated against whitelist
- Numeric fields validated for range and type
- Prevents SQL injection via parameterized queries
- Prevents duplicate sends to validated_results

---

## Testing Checklist

### Unit Tests (to be implemented)
- [ ] Inline edit updates field correctly
- [ ] Inline edit validates rating range (0-10)
- [ ] Inline edit validates price is positive
- [ ] Inline edit rejects invalid field names
- [ ] Inline edit sets is_edited flag
- [ ] Approve updates status to APPROVED
- [ ] Approve rejects already approved results
- [ ] Reject updates status to REJECTED
- [ ] Reject rejects already rejected results
- [ ] Send to validated creates validated_result record
- [ ] Send to validated only works for APPROVED results
- [ ] Send to validated prevents duplicate sends
- [ ] All endpoints require admin role (403 for non-admin)

### Integration Tests (to be implemented)
- [ ] Full workflow: edit → approve → send to validated
- [ ] Reject workflow: view → reject
- [ ] Status transitions work correctly
- [ ] validated_results record has correct foreign keys

---

## Implementation Status

### ✅ Completed
- [x] Database migration (0002_extend_validated_results_table.py)
- [x] Updated ValidatedResult model
- [x] Created admin_validation router
- [x] Implemented inline edit endpoint
- [x] Implemented approve endpoint
- [x] Implemented reject endpoint
- [x] Implemented send-to-validated endpoint
- [x] Registered router in main.py
- [x] Restarted backend service

### ⏳ Pending
- [ ] Unit tests for all endpoints
- [ ] Integration tests for workflows
- [ ] Frontend implementation
- [ ] End-to-end testing

---

## Next Steps

1. **Test Backend Endpoints**: Use Playwright browser console to test all endpoints
2. **Frontend Implementation**: Create inline editing UI, approve/reject buttons, send to validated button
3. **Integration Testing**: Test full workflow end-to-end
4. **Documentation**: Update user documentation with new features

---

**Document Version**: 1.0  
**Last Updated**: April 28, 2026  
**Author**: Kiro AI Agent
