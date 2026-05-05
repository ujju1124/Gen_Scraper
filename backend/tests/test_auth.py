"""
Integration tests for authentication endpoints.
"""
from datetime import datetime, timedelta
from jose import jwt
from config import settings
from models import User, RefreshToken
from services import auth_service


def test_register_creates_user(client, db_session):
    """POST /register creates a new user with role='user'."""
    response = client.post("/api/v1/auth/register", json={
        "email": "newuser@example.com",
        "password": "securepass123"
    })
    
    assert response.status_code == 201
    data = response.json()
    assert data["user"]["email"] == "newuser@example.com"
    assert data["user"]["role"] == "user"
    
    # Verify user exists in DB
    user = db_session.query(User).filter(User.email == "newuser@example.com").first()
    assert user is not None
    assert user.role == "user"
    assert user.is_active is True


def test_register_rejects_role_param(client, db_session):
    """POST /register ignores any role field — user is always created with role='user'."""
    # Pydantic schema doesn't accept 'role', so it should be ignored/rejected
    response = client.post("/api/v1/auth/register", json={
        "email": "hacker@example.com",
        "password": "securepass123",
        "role": "admin"  # This should be ignored
    })
    
    # Should succeed but role must be 'user'
    assert response.status_code == 201
    data = response.json()
    assert data["user"]["role"] == "user"
    
    # Verify in DB
    user = db_session.query(User).filter(User.email == "hacker@example.com").first()
    assert user is not None
    assert user.role == "user"  # Never admin


def test_register_rejects_duplicate_email(client, test_user):
    """POST /register returns 400 if email already exists."""
    response = client.post("/api/v1/auth/register", json={
        "email": test_user.email,
        "password": "anotherpass123"
    })
    
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"].lower()


def test_login_sets_httponly_cookies(client, test_user):
    """POST /login sets httpOnly access_token and refresh_token cookies."""
    response = client.post("/api/v1/auth/login", json={
        "email": test_user.email,
        "password": "testpass123"
    })
    
    assert response.status_code == 200
    
    # Check access_token cookie
    access_cookie = response.cookies.get("access_token")
    assert access_cookie is not None
    
    # Check cookie attributes via Set-Cookie header
    set_cookie_headers = response.headers.get_list("set-cookie") if hasattr(response.headers, "get_list") else [
        v for k, v in response.headers.items() if k.lower() == "set-cookie"
    ]
    
    cookie_str = " ".join(set_cookie_headers).lower()
    assert "httponly" in cookie_str
    assert "samesite=lax" in cookie_str


def test_login_rejects_wrong_password(client, test_user):
    """POST /login returns 401 for wrong password."""
    response = client.post("/api/v1/auth/login", json={
        "email": test_user.email,
        "password": "wrongpassword"
    })
    
    assert response.status_code == 401


def test_login_rejects_unknown_email(client):
    """POST /login returns 401 for unknown email."""
    response = client.post("/api/v1/auth/login", json={
        "email": "nobody@example.com",
        "password": "somepass123"
    })
    
    assert response.status_code == 401


def test_refresh_rotates_token(client, test_user, db_session):
    """POST /refresh issues a new access_token and rotates the refresh_token."""
    import time
    
    # Login first to get tokens
    login_resp = client.post("/api/v1/auth/login", json={
        "email": test_user.email,
        "password": "testpass123"
    })
    assert login_resp.status_code == 200
    
    original_access = client.cookies.get("access_token")
    
    # Wait 1 second to prevent JWT hash collision
    time.sleep(1)
    
    # Call refresh
    refresh_resp = client.post("/api/v1/auth/refresh")
    assert refresh_resp.status_code == 200
    
    new_access = client.cookies.get("access_token")
    
    # New access token should be different
    assert new_access is not None
    assert new_access != original_access


def test_refresh_rejects_invalid_token(client):
    """POST /refresh returns 401 if no valid refresh_token cookie."""
    # No cookies set
    response = client.post("/api/v1/auth/refresh")
    assert response.status_code == 401


def test_logout_clears_cookies(client, test_user):
    """POST /logout clears both access_token and refresh_token cookies."""
    # Login first
    client.post("/api/v1/auth/login", json={
        "email": test_user.email,
        "password": "testpass123"
    })
    
    # Logout
    response = client.post("/api/v1/auth/logout")
    assert response.status_code == 200
    
    # Cookies should be cleared (max_age=0 sets empty value)
    set_cookie_headers = [
        v for k, v in response.headers.items() if k.lower() == "set-cookie"
    ]
    cookie_str = " ".join(set_cookie_headers).lower()
    assert "max-age=0" in cookie_str


def test_expired_refresh_rejected(client, test_user, db_session):
    """POST /refresh returns 401 if refresh token is expired."""
    # Create an expired refresh token directly in DB
    expired_token = auth_service.create_refresh_token({"sub": str(test_user.id)})
    token_hash = __import__("hashlib").sha256(expired_token.encode()).hexdigest()
    
    from models import RefreshToken
    expired = RefreshToken(
        user_id=test_user.id,
        token_hash=token_hash,
        expires_at=datetime.utcnow() - timedelta(days=1),  # Already expired
        revoked=False
    )
    db_session.add(expired)
    db_session.commit()
    
    # Set the expired token as cookie
    client.cookies.set("refresh_token", expired_token)
    
    response = client.post("/api/v1/auth/refresh")
    assert response.status_code == 401


def test_me_returns_db_role(client, test_user):
    """GET /me returns role read from DB, not from JWT payload."""
    # Set access token cookie
    access_token = auth_service.create_access_token({"sub": str(test_user.id)})
    client.cookies.set("access_token", access_token)
    
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 200
    
    data = response.json()
    assert data["id"] == test_user.id
    assert data["email"] == test_user.email
    assert data["role"] == "user"  # Role from DB, not JWT


def test_me_requires_auth(client):
    """GET /me returns 401 if no access_token cookie."""
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
