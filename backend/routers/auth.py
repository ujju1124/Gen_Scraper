"""
Authentication routes.
Handles user registration, login, token refresh, logout, and user info.
"""
from fastapi import APIRouter, Depends, HTTPException, Response, Request, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, ConfigDict

from dependencies import get_db, get_current_user
from models import User
from services import auth_service
from config import settings

router = APIRouter()


# Request/Response schemas
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    email: str
    role: str
    
    model_config = ConfigDict(from_attributes=True)


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(
    request: RegisterRequest,
    response: Response,
    db: Session = Depends(get_db)
):
    """
    Register a new user.
    
    - Accepts email and password only
    - Rejects any 'role' parameter
    - Creates user with role='user' only
    - Returns 400 if email already exists
    """
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Hash password
    password_hash = auth_service.hash_password(request.password)
    
    # Create user with role='user' (never accept role from request)
    user = User(
        email=request.email,
        password_hash=password_hash,
        role="user",
        is_active=True
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return {
        "message": "User registered successfully",
        "user": {
            "id": user.id,
            "email": user.email,
            "role": user.role
        }
    }


@router.post("/login")
def login(
    request: LoginRequest,
    response: Response,
    db: Session = Depends(get_db)
):
    """
    Login and receive access + refresh tokens as httpOnly cookies.
    
    - Verifies credentials
    - Generates access token (15 min) and refresh token (7 days)
    - Sets httpOnly cookies with appropriate security settings
    """
    # Find user by email
    user = db.query(User).filter(User.email == request.email).first()
    
    if not user or not auth_service.verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    # Generate tokens
    access_token = auth_service.create_access_token({"sub": str(user.id)})
    refresh_token = auth_service.create_refresh_token({"sub": str(user.id)})
    
    # Store refresh token in database
    auth_service.store_refresh_token(db, user.id, refresh_token)
    
    # Determine if we're in production (use secure cookies)
    is_production = settings.ENV == "production"
    
    # Set access_token cookie
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=False,  # Allow HTTP in development (Docker)
        samesite="lax",
        max_age=900,  # 15 minutes
        path="/",
        domain=None  # Let browser handle domain
    )
    
    # Set refresh_token cookie
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=False,  # Allow HTTP in development (Docker)
        samesite="lax",
        max_age=604800,  # 7 days
        path="/",  # Changed from /api/v1/auth/refresh to / for nginx proxy
        domain=None  # Let browser handle domain
    )
    
    return {
        "message": "Login successful",
        "user": {
            "id": user.id,
            "email": user.email,
            "role": user.role
        }
    }


@router.post("/refresh/")
def refresh(
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    """
    Refresh access token using refresh token.
    
    - Reads refresh_token from cookie
    - Rotates tokens (revokes old, issues new)
    - Sets new access_token cookie
    - Returns 401 if token is invalid, expired, or revoked
    """
    # Read refresh_token from cookie
    refresh_token = request.cookies.get("refresh_token")
    
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token missing"
        )
    
    # Rotate tokens
    result = auth_service.rotate_refresh_token(db, refresh_token)
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )
    
    new_access_token, new_refresh_token = result
    
    # Determine if we're in production
    is_production = settings.ENV == "production"
    
    # Set new access_token cookie
    response.set_cookie(
        key="access_token",
        value=new_access_token,
        httponly=True,
        secure=False,  # Allow HTTP in development
        samesite="lax",
        max_age=900,  # 15 minutes
        path="/",
        domain=None
    )
    
    # Set new refresh_token cookie
    response.set_cookie(
        key="refresh_token",
        value=new_refresh_token,
        httponly=True,
        secure=False,  # Allow HTTP in development
        samesite="lax",
        max_age=604800,  # 7 days
        path="/",  # Changed from /api/v1/auth/refresh
        domain=None
    )
    
    return {"message": "Token refreshed successfully"}


@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    """
    Logout and revoke refresh token.
    
    - Revokes refresh token in database
    - Clears both cookies by setting max_age=0
    """
    # Read refresh_token from cookie
    refresh_token = request.cookies.get("refresh_token")
    
    if refresh_token:
        # Revoke the refresh token
        auth_service.revoke_refresh_token(db, refresh_token)
    
    # Determine if we're in production
    is_production = settings.ENV == "production"
    
    # Clear both cookies by setting max_age=0
    response.set_cookie(
        key="access_token",
        value="",
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=0,
        path="/",
        domain=None
    )
    response.set_cookie(
        key="refresh_token",
        value="",
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=0,
        path="/",  # Changed from /api/v1/auth/refresh
        domain=None
    )
    
    return {"message": "Logout successful"}


@router.get("/me", response_model=UserResponse)
def get_me(
    current_user: User = Depends(get_current_user)
):
    """
    Get current user information.
    
    - Returns user id, email, and role
    - Role is read from database via get_current_user dependency
    - Never reads role from JWT payload
    """
    return current_user
