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
    
    # Go scraper microservice settings
    GO_SCRAPER_URL: str = "http://go_scraper:8080"
    GO_SCRAPER_API_KEY: str = ""
    GO_SCRAPER_ENABLED: bool = True
    GO_SCRAPER_TIMEOUT: int = 600   # seconds to wait for Go job to complete (10 minutes including queue wait)
    GO_SCRAPER_POLL_INTERVAL: int = 5  # seconds between status polls
    
    # Detail page scraping settings
    MAX_DETAIL_PAGES_PER_JOB: int = 0  # Set to 0 or None for unlimited, or positive number to limit
    DETAIL_PAGE_DELAY_MIN: int = 1000  # milliseconds (reduced from 3000 to 1000)
    DETAIL_PAGE_DELAY_MAX: int = 2000  # milliseconds (reduced from 6000 to 2000)
    
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
