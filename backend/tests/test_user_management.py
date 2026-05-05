"""
Tests for user management endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from main import app
from models import User


def test_get_users_returns_paginated_list(admin_client: TestClient, db_session: Session, test_user: User):
    """Test GET /api/v1/admin/users returns paginated user list"""
    response = admin_client.get("/api/v1/admin/users")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data
    assert "pages" in data
    
    assert data["page"] == 1
    assert data["page_size"] == 20
    assert data["total"] >= 2  # At least admin and test_user
    
    # Check user structure
    assert len(data["items"]) >= 2
    user_item = data["items"][0]
    assert "id" in user_item
    assert "email" in user_item
    assert "role" in user_item
    assert "is_active" in user_item
    assert "created_at" in user_item


def test_get_users_pagination_works(admin_client: TestClient, db_session: Session):
    """Test GET /api/v1/admin/users pagination parameters work"""
    response = admin_client.get("/api/v1/admin/users?page=1&page_size=1")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["page"] == 1
    assert data["page_size"] == 1
    assert len(data["items"]) == 1


def test_get_users_non_admin_forbidden(auth_client: TestClient, db_session: Session):
    """Test GET /api/v1/admin/users returns 403 for non-admin"""
    response = auth_client.get("/api/v1/admin/users")
    
    assert response.status_code == 403
    assert "Admin access required" in response.json()["detail"]


def test_patch_user_activate(admin_client: TestClient, db_session: Session, test_user: User):
    """Test PATCH /api/v1/admin/users/{id} activates user"""
    # First deactivate the user
    test_user.is_active = False
    db_session.commit()
    
    # Now activate via API
    response = admin_client.patch(
        f"/api/v1/admin/users/{test_user.id}",
        json={"is_active": True}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["id"] == test_user.id
    assert data["email"] == test_user.email
    assert data["is_active"] is True
    
    # Verify in database
    db_session.refresh(test_user)
    assert test_user.is_active is True


def test_patch_user_deactivate(admin_client: TestClient, db_session: Session, test_user: User):
    """Test PATCH /api/v1/admin/users/{id} deactivates user"""
    # Ensure user is active
    test_user.is_active = True
    db_session.commit()
    
    # Deactivate via API
    response = admin_client.patch(
        f"/api/v1/admin/users/{test_user.id}",
        json={"is_active": False}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["id"] == test_user.id
    assert data["is_active"] is False
    
    # Verify in database
    db_session.refresh(test_user)
    assert test_user.is_active is False


def test_patch_user_admin_cannot_deactivate_self(admin_client: TestClient, db_session: Session, test_admin: User):
    """Test admin cannot deactivate their own account"""
    response = admin_client.patch(
        f"/api/v1/admin/users/{test_admin.id}",
        json={"is_active": False}
    )
    
    assert response.status_code == 400
    assert "Cannot deactivate your own account" in response.json()["detail"]
    
    # Verify admin is still active
    db_session.refresh(test_admin)
    assert test_admin.is_active is True


def test_patch_user_admin_can_activate_self(admin_client: TestClient, db_session: Session, test_admin: User):
    """Test admin can activate their own account (edge case, but allowed)"""
    response = admin_client.patch(
        f"/api/v1/admin/users/{test_admin.id}",
        json={"is_active": True}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["is_active"] is True


def test_patch_user_non_admin_forbidden(auth_client: TestClient, db_session: Session, test_user: User):
    """Test PATCH /api/v1/admin/users/{id} returns 403 for non-admin"""
    # Ensure test_user is active (may have been deactivated by previous test)
    test_user.is_active = True
    db_session.commit()
    
    response = auth_client.patch(
        f"/api/v1/admin/users/{test_user.id}",
        json={"is_active": False}
    )
    
    assert response.status_code == 403
    assert "Admin access required" in response.json()["detail"]


def test_patch_user_not_found(admin_client: TestClient, db_session: Session):
    """Test PATCH /api/v1/admin/users/{id} returns 404 for non-existent user"""
    response = admin_client.patch(
        "/api/v1/admin/users/99999",
        json={"is_active": False}
    )
    
    assert response.status_code == 404
    assert "User not found" in response.json()["detail"]


def test_get_users_unauthenticated(client: TestClient, db_session: Session):
    """Test GET /api/v1/admin/users returns 401 without token"""
    response = client.get("/api/v1/admin/users")
    
    assert response.status_code == 401


def test_patch_user_unauthenticated(client: TestClient, db_session: Session, test_user: User):
    """Test PATCH /api/v1/admin/users/{id} returns 401 without token"""
    response = client.patch(
        f"/api/v1/admin/users/{test_user.id}",
        json={"is_active": False}
    )
    
    assert response.status_code == 401
