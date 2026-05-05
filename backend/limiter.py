"""
Rate limiter configuration.
Centralized limiter instance to avoid circular imports.
"""
from slowapi import Limiter
from fastapi import Request
from slowapi.util import get_remote_address
from jose import jwt, JWTError
from config import settings


def get_user_id_or_ip(request: Request) -> str:
    """
    Extract user ID from access_token cookie for rate limiting.
    Falls back to IP address if no valid token.
    """
    token = request.cookies.get("access_token")
    if token:
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
            user_id = payload.get("sub")
            if user_id:
                return f"user:{user_id}"
        except JWTError:
            pass
    return get_remote_address(request)


limiter = Limiter(key_func=get_user_id_or_ip)
