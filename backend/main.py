"""
FastAPI application entry point.
Configures structlog, Sentry, CORS, rate limiting, and mounts all routers.
"""
import structlog
import sentry_sdk
import redis as redis_lib
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.celery import CeleryIntegration

from config import settings
from database import SessionLocal, engine
from sqlalchemy import text
from limiter import limiter

# Configure structlog for JSON logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer(),
    ]
)

logger = structlog.get_logger()

# Initialize Sentry if DSN is provided
if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        integrations=[
            FastApiIntegration(),
            CeleryIntegration(),
        ],
        traces_sample_rate=0.1,  # 10% performance tracing
        environment=settings.ENV,
        send_default_pii=False,  # Never send user PII to Sentry
    )
    logger.info("sentry.initialized", environment=settings.ENV)
else:
    logger.info("sentry.disabled", reason="SENTRY_DSN not set")

# Create FastAPI app
app = FastAPI(
    title="Web Scraping Portal API",
    description="Production-grade web scraping portal for Nepal business data",
    version="1.0.0",
)

# Configure CORS
# In development, allow multiple ports for Vite dev server
if settings.ENV == "development":
    allowed_origins = [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:5175",
    ]
else:
    allowed_origins = [settings.FRONTEND_URL]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add security headers to all responses."""
    response = await call_next(request)
    
    # Prevent MIME sniffing attacks
    response.headers["X-Content-Type-Options"] = "nosniff"
    
    # Prevent clickjacking attacks
    response.headers["X-Frame-Options"] = "DENY"
    
    # Control referrer information leakage
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    
    # Content Security Policy (unsafe-inline needed for React inline styles)
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "font-src 'self' data:; "
        "connect-src 'self'"
    )
    
    # HTTPS-only in production (HSTS)
    if settings.ENV == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    
    return response

# Configure rate limiting (limiter imported from limiter.py)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Global exception handler to prevent information disclosure
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler to prevent stack trace leakage.
    Logs full error details but returns generic message to client.
    """
    # Log full error with stack trace (for debugging)
    logger.error(
        "unhandled_exception",
        error=str(exc),
        error_type=type(exc).__name__,
        path=request.url.path,
        method=request.method,
        exc_info=True  # Full stack trace in logs only
    )
    
    # Return generic error to client (NO stack trace, NO file paths)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error"
        }
    )

# Health check endpoint (not under /api/v1/)
@app.get("/health")
async def health_check():
    """
    Health check endpoint.
    Verifies database and Redis connectivity.
    """
    try:
        # Check database connectivity
        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
            db_healthy = True
        except Exception as e:
            logger.error("health.db_check_failed", error=str(e))
            db_healthy = False
        finally:
            db.close()
        
        # Check Redis connectivity
        try:
            r = redis_lib.from_url(settings.REDIS_URL)
            r.ping()
            redis_healthy = True
        except Exception as e:
            logger.error("health.redis_check_failed", error=str(e))
            redis_healthy = False
        
        if db_healthy and redis_healthy:
            return {"status": "healthy"}
        else:
            detail = []
            if not db_healthy:
                detail.append("database unreachable")
            if not redis_healthy:
                detail.append("redis unreachable")
            return JSONResponse(
                status_code=503,
                content={"status": "unhealthy", "detail": ", ".join(detail)}
            )
    except Exception as e:
        logger.error("health.check_failed", error=str(e), exc_info=True)
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "detail": str(e)}
        )

# Mount routers (will be added in subsequent tasks)
from routers import auth, jobs, admin, categories, admin_sources, admin_validation, validated, image_proxy
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(jobs.router, prefix="/api/v1/jobs", tags=["jobs"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["admin"])
app.include_router(admin_sources.router, prefix="/api/v1/admin", tags=["admin-sources"])
app.include_router(admin_validation.router, prefix="/api/v1/admin", tags=["admin-validation"])
app.include_router(categories.router, prefix="/api/v1/categories", tags=["categories"])
app.include_router(validated.router, prefix="/api/v1/validated", tags=["validated"])
app.include_router(image_proxy.router, prefix="/api/v1/images", tags=["images"])

logger.info("app.started", environment=settings.ENV, frontend_url=settings.FRONTEND_URL)
