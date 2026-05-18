from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    # Environment
    ENV: str = "development"
    
    # Required fields - no defaults, will raise validation error if missing
    SECRET_KEY: str
    DATABASE_URL: str
    REDIS_URL: str
    ADMIN_PASSWORD: str
    ADMIN_EMAIL: str
    
    # Optional fields with defaults
    SENTRY_DSN: str = ""
    FRONTEND_URL: str = "http://localhost:5173"
    CELERY_CONCURRENCY: int = 2
    
    # JWT settings
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"
    
    # Scraper settings
    MOCK_MODE: bool = False
    
    # Detail page scraping settings
    MAX_DETAIL_PAGES_PER_JOB: int = 10
    DETAIL_PAGE_DELAY_MIN: int = 3000  # milliseconds
    DETAIL_PAGE_DELAY_MAX: int = 6000  # milliseconds
    
    # Geocoding settings
    GEOCODING_ENABLED: bool = True
    OVERPASS_API_URL: str = "https://overpass-api.de/api/interpreter"
    GEOCODING_TIMEOUT: int = 10  # seconds
    GEOCODING_RATE_LIMIT: float = 1.0  # requests per second
    
    # Data retention settings
    RAW_RESULTS_RETENTION_DAYS: int = 90
    
    model_config = ConfigDict(env_file=".env", case_sensitive=True, extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
