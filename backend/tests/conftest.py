"""
Pytest configuration and fixtures for integration tests.
"""
import os
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from alembic.config import Config
from alembic import command

from main import app
from database import Base
from dependencies import get_db
from models import User, Category, Source
from services import auth_service
from tasks.scrape_task import celery_app

# Test database URL (separate from development database)
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql://scraper:scraper_pass@postgres:5432/scraper_test_db"
)

# Create test engine
test_engine = create_engine(TEST_DATABASE_URL)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """
    Setup test database before test session starts.
    Creates database, runs Alembic migrations, and seeds required data.
    """
    # Derive the postgres connection URL from TEST_DATABASE_URL
    # Replace the database name with 'postgres' to connect to default database
    import re
    postgres_url = re.sub(r'/[^/]+$', '/postgres', TEST_DATABASE_URL)
    
    # Create test database if it doesn't exist
    default_engine = create_engine(postgres_url)
    conn = default_engine.connect()
    conn.execution_options(isolation_level="AUTOCOMMIT")
    
    # Terminate existing connections to test database
    conn.execute(text("""
        SELECT pg_terminate_backend(pg_stat_activity.pid)
        FROM pg_stat_activity
        WHERE pg_stat_activity.datname = 'scraper_test_db'
        AND pid <> pg_backend_pid()
    """))
    
    # Drop and recreate test database
    conn.execute(text("DROP DATABASE IF EXISTS scraper_test_db"))
    conn.execute(text("CREATE DATABASE scraper_test_db"))
    conn.close()
    default_engine.dispose()
    
    # Run Alembic migrations on test database
    import os
    alembic_cfg = Config(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))
    alembic_cfg.set_main_option("script_location", os.path.join(os.path.dirname(__file__), "..", "alembic"))
    alembic_cfg.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)
    command.upgrade(alembic_cfg, "head")
    
    # Seed required data (categories and placeholder source)
    db = TestSessionLocal()
    try:
        # Insert placeholder category
        db.execute(text("""
            INSERT INTO categories (id, name, display_name)
            VALUES (1, 'hotels', 'Hotels')
            ON CONFLICT (id) DO NOTHING
        """))
        
        # Insert placeholder source for fake scraper
        db.execute(text("""
            INSERT INTO sources (id, name, display_name, category_id, base_url, heal_mode)
            VALUES (1, 'fake_source', 'Fake Source', 1, 'http://example.com', 'MANUAL')
            ON CONFLICT DO NOTHING
        """))
        
        db.commit()
    finally:
        db.close()
    
    yield
    
    # Cleanup after all tests
    test_engine.dispose()


@pytest.fixture(scope="session", autouse=True)
def configure_celery():
    """
    Configure Celery for synchronous execution in tests.
    Uses task_always_eager=True (Celery 5+ compatible).
    """
    celery_app.conf.update(
        task_always_eager=True,
        task_eager_propagates=True
    )
    yield


@pytest.fixture(scope="function")
def db_session():
    """
    Provide a database session for each test.
    Does NOT use transaction rollback because Celery tasks need to see committed data.
    Cleanup is handled by the cleanup_job_data fixture and table truncation.
    
    IMPORTANT: This fixture also patches database.SessionLocal so that Celery tasks
    use the same session as the test, allowing them to see committed data.
    """
    session = TestSessionLocal()
    
    # Patch SessionLocal to return a function that yields the test session
    # This makes Celery tasks use the same database session as the test
    from unittest.mock import patch, MagicMock
    
    # Create a mock that returns the test session
    mock_session_factory = MagicMock(return_value=session)
    
    with patch("tasks.scrape_task.SessionLocal", mock_session_factory):
        yield session
    
    session.close()


@pytest.fixture(scope="function")
def client(db_session):
    """
    Provide a test client with overridden database dependency.
    """
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def test_user(db_session):
    """
    Create a test user with role='user'.
    Reuses existing user if already present.
    """
    # Check if user already exists
    user = db_session.query(User).filter(User.email == "testuser@example.com").first()
    if user:
        return user
    
    # Create new user with short password (bcrypt has 72 byte limit)
    user = User(
        email="testuser@example.com",
        password_hash=auth_service.hash_password("testpass123"),
        role="user",
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def test_admin(db_session):
    """
    Create a test admin user with role='admin'.
    Reuses existing admin if already present.
    """
    # Check if admin already exists
    admin = db_session.query(User).filter(User.email == "testadmin@example.com").first()
    if admin:
        return admin
    
    # Create new admin with short password (bcrypt has 72 byte limit)
    admin = User(
        email="testadmin@example.com",
        password_hash=auth_service.hash_password("adminpass"),
        role="admin",
        is_active=True
    )
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)
    return admin


@pytest.fixture(scope="function")
def auth_client(db_session, test_user):
    """
    Provide a test client with valid access_token cookie.
    Creates its own client instance to avoid conflicts with other client fixtures.
    """
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        # Generate access token
        access_token = auth_service.create_access_token({"sub": str(test_user.id)})
        
        # Set cookie on client
        test_client.cookies.set("access_token", access_token)
        
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def admin_client(db_session, test_admin):
    """
    Provide a test client with valid admin access_token cookie.
    Creates its own client instance to avoid conflicts with auth_client.
    """
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        # Generate access token
        access_token = auth_service.create_access_token({"sub": str(test_admin.id)})
        
        # Set cookie on client
        test_client.cookies.set("access_token", access_token)
        
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def mock_sleep():
    """
    Mock time.sleep to avoid long test runs.
    The fake scraper sleeps 3-8 seconds, which would make tests very slow.
    """
    with patch("tasks.scrape_task.time.sleep") as mock:
        yield mock


@pytest.fixture(scope="function", autouse=True)
def cleanup_job_data():
    """
    Truncate job-related tables after each test.
    Needed because the Celery task opens its own SessionLocal() session,
    and we're not using transaction rollback anymore.
    
    Note: We don't truncate users table because test_user and test_admin fixtures
    create users that are needed across tests.
    """
    yield
    db = TestSessionLocal()
    try:
        # Truncate in correct order (respecting foreign keys)
        # Don't truncate users - let test fixtures manage user lifecycle
        db.execute(text("TRUNCATE raw_results, cleaned_results, validated_results, scrape_jobs, refresh_tokens CASCADE"))
        db.commit()
    finally:
        db.close()


@pytest.fixture(autouse=True)
def mock_asyncio_run(request):
    """
    Mock asyncio.run() for test_jobs.py tests only.
    
    This prevents the "asyncio.run() cannot be called from a running event loop" error
    that occurs when Celery tasks run synchronously (task_always_eager=True) inside
    TestClient's event loop.
    
    The mock executes the coroutine synchronously and returns fake scrape results.
    """
    from unittest.mock import MagicMock
    import asyncio
    
    # Only mock for test_jobs.py tests
    if 'test_jobs' not in request.node.nodeid:
        yield
        return
    
    # Store the original asyncio.run
    original_run = asyncio.run
    
    def mock_run(coro):
        """
        Mock asyncio.run that executes the coroutine in the current event loop.
        Returns fake data for orchestrator.run_async() calls.
        """
        # Check if this is an orchestrator call by inspecting the coroutine
        coro_name = coro.__qualname__ if hasattr(coro, '__qualname__') else str(coro)
        
        if 'run_async' in str(coro_name) or 'ScraperOrchestrator' in str(type(coro)):
            # Return fake scrape results for orchestrator calls
            return (
                # 10 fake raw results
                [
                    {
                        "name": f"Test Hotel {i+1}",
                        "address": f"{i+1} Test Street",
                        "city": "Kathmandu",
                        "phone": "+977-1-4000000",
                        "email": f"hotel{i+1}@example.com",
                        "website": f"https://hotel{i+1}.example.com",
                    }
                    for i in range(10)
                ],
                []  # Empty failed_source_ids
            )
        elif 'geocode' in str(coro_name):
            # Return 0 for geocoding calls
            return 0
        else:
            # For other coroutines, try to run them normally
            try:
                return original_run(coro)
            except RuntimeError:
                # If we can't run it, return None
                return None
    
    # Patch asyncio.run in the tasks.scrape_task module
    with patch('tasks.scrape_task.asyncio.run', side_effect=mock_run):
        yield
