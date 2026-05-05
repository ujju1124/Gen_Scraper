"""
Authentication service.
Handles password hashing, JWT token generation, and refresh token management.
"""
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from passlib.context import CryptContext
from jose import jwt, JWTError
from sqlalchemy.orm import Session

from config import settings
from models import RefreshToken

# Password hashing context
# Configure bcrypt to truncate passwords at 72 bytes (bcrypt's limit)
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12,
    bcrypt__truncate_error=False  # Automatically truncate instead of raising error
)

# Token expiry times
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.
    Bcrypt has a 72-byte limit, so we truncate passwords to 72 bytes.
    
    Args:
        password: Plain text password
        
    Returns:
        Bcrypt hashed password
    """
    # Truncate password to 72 bytes (bcrypt's limit)
    password_bytes = password.encode('utf-8')[:72]
    truncated_password = password_bytes.decode('utf-8', errors='ignore')
    return pwd_context.hash(truncated_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.
    Bcrypt has a 72-byte limit, so we truncate passwords to 72 bytes.
    
    Args:
        plain_password: Plain text password to verify
        hashed_password: Bcrypt hashed password
        
    Returns:
        True if password matches, False otherwise
    """
    # Truncate password to 72 bytes (bcrypt's limit)
    password_bytes = plain_password.encode('utf-8')[:72]
    truncated_password = password_bytes.decode('utf-8', errors='ignore')
    return pwd_context.verify(truncated_password, hashed_password)


def create_access_token(data: Dict[str, Any]) -> str:
    """
    Create a JWT access token.
    
    Args:
        data: Payload data to encode in the token (typically {"sub": user_id})
        
    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
    return encoded_jwt


def create_refresh_token(data: Dict[str, Any]) -> str:
    """
    Create a JWT refresh token.
    
    Args:
        data: Payload data to encode in the token (typically {"sub": user_id})
        
    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
    return encoded_jwt


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode and verify a JWT token.
    
    Args:
        token: JWT token string
        
    Returns:
        Decoded payload if valid, None if invalid or expired
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        return payload
    except JWTError:
        return None


def store_refresh_token(db: Session, user_id: int, token: str) -> RefreshToken:
    """
    Store a refresh token in the database.
    Stores SHA-256 hash of the token, not the raw value.
    
    Args:
        db: Database session
        user_id: User ID
        token: Raw refresh token string
        
    Returns:
        Created RefreshToken model instance
    """
    # Hash the token with SHA-256
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    
    # Calculate expiry
    expires_at = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    # Create and store the refresh token
    refresh_token = RefreshToken(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=expires_at,
        revoked=False
    )
    
    db.add(refresh_token)
    db.commit()
    db.refresh(refresh_token)
    
    return refresh_token


def rotate_refresh_token(db: Session, old_token: str) -> Optional[tuple[str, str]]:
    """
    Rotate a refresh token (revoke old, issue new).
    
    Args:
        db: Database session
        old_token: Current refresh token string
        
    Returns:
        Tuple of (new_access_token, new_refresh_token) if successful, None if invalid
    """
    # Hash the old token to look it up
    token_hash = hashlib.sha256(old_token.encode()).hexdigest()
    
    # Find the token in the database
    refresh_token = db.query(RefreshToken).filter(
        RefreshToken.token_hash == token_hash,
        RefreshToken.revoked == False,
        RefreshToken.expires_at > datetime.utcnow()
    ).first()
    
    if not refresh_token:
        return None
    
    # Revoke the old token
    refresh_token.revoked = True
    db.commit()
    
    # Create new tokens
    user_id = refresh_token.user_id
    new_access_token = create_access_token({"sub": str(user_id)})
    new_refresh_token = create_refresh_token({"sub": str(user_id)})
    
    # Store the new refresh token
    store_refresh_token(db, user_id, new_refresh_token)
    
    return (new_access_token, new_refresh_token)


def revoke_refresh_token(db: Session, token: str) -> bool:
    """
    Revoke a refresh token (logout).
    
    Args:
        db: Database session
        token: Refresh token string to revoke
        
    Returns:
        True if token was revoked, False if not found
    """
    # Hash the token to look it up
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    
    # Find and revoke the token
    refresh_token = db.query(RefreshToken).filter(
        RefreshToken.token_hash == token_hash
    ).first()
    
    if not refresh_token:
        return False
    
    refresh_token.revoked = True
    db.commit()
    
    return True
