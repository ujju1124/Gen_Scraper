"""
Tests for bulk action endpoint.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from uuid import uuid4

from main import app
from models import User, CleanedResult, ScrapeJob, ValidatedResult


def test_bulk_approve_moves_to_validated(client: TestClient, db_session: Session, test_admin: User):
    """Test bulk approve moves 3 records to validated_results."""
    # Create a test job
    job = ScrapeJob(
        user_id=test_admin.id,
        category_id=1,
        location="Kathmandu",
        status="DONE"
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    
    # Create 3 test results with PENDING status
    results = []
    for i in range(3):
        result = CleanedResult(
            job_id=job.id,
            source_id=1,
            category_id=1,
            name=f"Test Business {i+1}",
            status="PENDING"
        )
        db_session.add(result)
        results.append(result)
    
    db_session.commit()
    for result in results:
        db_session.refresh(result)
    
    # Get result IDs
    result_ids = [str(result.id) for result in results]
    
    # Override get_current_user to return admin
    from dependencies import get_current_user
    
    def override_get_current_user():
        return test_admin
    
    app.dependency_overrides[get_current_user] = override_get_current_user
    
    try:
        # Call bulk approve
        response = client.post(
            "/api/v1/admin/results/bulk-action",
            json={"ids": result_ids, "action": "approve"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["processed"] == 3
        assert data["action"] == "approve"
        
        # Verify all results are now APPROVED
        for result_id in result_ids:
            result = db_session.query(CleanedResult).filter(
                CleanedResult.id == result_id
            ).first()
            assert result.status == "APPROVED"
        
    finally:
        app.dependency_overrides.clear()


def test_bulk_reject_marks_rejected(client: TestClient, db_session: Session, test_admin: User):
    """Test bulk reject marks 3 records as REJECTED."""
    # Create a test job
    job = ScrapeJob(
        user_id=test_admin.id,
        category_id=1,
        location="Kathmandu",
        status="DONE"
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    
    # Create 3 test results with PENDING status
    results = []
    for i in range(3):
        result = CleanedResult(
            job_id=job.id,
            source_id=1,
            category_id=1,
            name=f"Test Business {i+1}",
            status="PENDING"
        )
        db_session.add(result)
        results.append(result)
    
    db_session.commit()
    for result in results:
        db_session.refresh(result)
    
    # Get result IDs
    result_ids = [str(result.id) for result in results]
    
    # Override get_current_user to return admin
    from dependencies import get_current_user
    
    def override_get_current_user():
        return test_admin
    
    app.dependency_overrides[get_current_user] = override_get_current_user
    
    try:
        # Call bulk reject
        response = client.post(
            "/api/v1/admin/results/bulk-action",
            json={"ids": result_ids, "action": "reject"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["processed"] == 3
        assert data["action"] == "reject"
        
        # Verify all results are now REJECTED
        for result_id in result_ids:
            result = db_session.query(CleanedResult).filter(
                CleanedResult.id == result_id
            ).first()
            assert result.status == "REJECTED"
        
    finally:
        app.dependency_overrides.clear()


def test_bulk_action_non_admin_gets_403(client: TestClient, db_session: Session, test_user: User):
    """Test non-admin user gets 403."""
    # Override get_current_user to return regular user
    from dependencies import get_current_user
    
    def override_get_current_user():
        return test_user
    
    app.dependency_overrides[get_current_user] = override_get_current_user
    
    try:
        response = client.post(
            "/api/v1/admin/results/bulk-action",
            json={"ids": [str(uuid4())], "action": "approve"}
        )
        
        assert response.status_code == 403
        
    finally:
        app.dependency_overrides.clear()


def test_bulk_action_empty_ids_returns_400(client: TestClient, test_admin: User):
    """Test empty ids list returns 400."""
    from dependencies import get_current_user
    
    def override_get_current_user():
        return test_admin
    
    app.dependency_overrides[get_current_user] = override_get_current_user
    
    try:
        response = client.post(
            "/api/v1/admin/results/bulk-action",
            json={"ids": [], "action": "approve"}
        )
        
        assert response.status_code == 400
        assert "empty" in response.json()["detail"].lower()
        
    finally:
        app.dependency_overrides.clear()


def test_bulk_action_invalid_action_returns_400(client: TestClient, test_admin: User):
    """Test invalid action returns 400."""
    from dependencies import get_current_user
    
    def override_get_current_user():
        return test_admin
    
    app.dependency_overrides[get_current_user] = override_get_current_user
    
    try:
        response = client.post(
            "/api/v1/admin/results/bulk-action",
            json={"ids": [str(uuid4())], "action": "invalid"}
        )
        
        assert response.status_code == 400
        assert "action must be" in response.json()["detail"].lower()
        
    finally:
        app.dependency_overrides.clear()


def test_bulk_action_mixed_valid_invalid_ids(client: TestClient, db_session: Session, test_admin: User):
    """Test mix of valid and invalid IDs — processes valid ones, skips missing."""
    # Create a test job
    job = ScrapeJob(
        user_id=test_admin.id,
        category_id=1,
        location="Kathmandu",
        status="DONE"
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    
    # Create 2 valid results
    valid_results = []
    for i in range(2):
        result = CleanedResult(
            job_id=job.id,
            source_id=1,
            category_id=1,
            name=f"Valid Business {i+1}",
            status="PENDING"
        )
        db_session.add(result)
        valid_results.append(result)
    
    db_session.commit()
    for result in valid_results:
        db_session.refresh(result)
    
    # Mix valid IDs with non-existent IDs and invalid UUID strings
    mixed_ids = [
        str(valid_results[0].id),
        str(uuid4()),  # Non-existent but valid UUID
        str(valid_results[1].id),
        "not-a-uuid",  # Invalid UUID string
        str(uuid4()),  # Another non-existent UUID
    ]
    
    # Override get_current_user to return admin
    from dependencies import get_current_user
    
    def override_get_current_user():
        return test_admin
    
    app.dependency_overrides[get_current_user] = override_get_current_user
    
    try:
        # Call bulk approve
        response = client.post(
            "/api/v1/admin/results/bulk-action",
            json={"ids": mixed_ids, "action": "approve"}
        )
        
        assert response.status_code == 200
        data = response.json()
        # Should only process the 2 valid existing results
        assert data["processed"] == 2
        assert data["action"] == "approve"
        
        # Verify the 2 valid results are APPROVED
        for result in valid_results:
            db_session.refresh(result)
            assert result.status == "APPROVED"
        
    finally:
        app.dependency_overrides.clear()
