"""
FastAPI dependencies.
Provides database session and authentication dependencies.
"""
from typing import Generator
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from database import SessionLocal
from models import User
from services import auth_service


def get_db() -> Generator[Session, None, None]:
    """
    Database session dependency.
    Creates a new SQLAlchemy session for each request and closes it after.
    
    Yields:
        Database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    request: Request,
    db: Session = Depends(get_db)
) -> User:
    """
    Get the current authenticated user from the access_token cookie.
    Loads the user from the database including their role.
    
    Args:
        request: FastAPI request object
        db: Database session
        
    Returns:
        User model instance
        
    Raises:
        HTTPException: 401 if token is missing, invalid, or expired
        HTTPException: 403 if user is inactive
    """
    # Read access_token from cookie
    access_token = request.cookies.get("access_token")
    
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    # Decode the token
    payload = auth_service.decode_token(access_token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    # Extract user ID from token
    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
    
    try:
        user_id = int(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
    
    # Load user from database (including role)
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    return user


def require_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Require the current user to have admin role.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        User model instance (if admin)
        
    Raises:
        HTTPException: 403 if user is not an admin
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    return current_user
