"""
Tests for email service.
"""
import pytest
import os
from unittest.mock import patch, MagicMock, AsyncMock
from sqlalchemy.orm import Session
from uuid import uuid4

from services.email_service import (
    get_smtp_config,
    get_frontend_url,
    build_success_email,
    build_failure_email,
    send_job_completion_email
)
from models import User, ScrapeJob, Category, CleanedResult


@pytest.fixture
def mock_smtp_config():
    """Mock SMTP configuration"""
    return {
        "host": "smtp.example.com",
        "port": 587,
        "username": "test@example.com",
        "password": "test_password",
        "from_email": "noreply@example.com",
        "use_tls": True
    }


@pytest.fixture
def test_job_done(db_session: Session, test_user: User):
    """Create a test job with DONE status"""
    # Create category if it doesn't exist
    category = db_session.query(Category).filter(Category.id == 10).first()
    if not category:
        category = Category(id=10, name="test_hotels", display_name="Test Hotels")
        db_session.add(category)
        db_session.commit()
    
    # Create job
    job = ScrapeJob(
        user_id=test_user.id,
        category_id=10,
        location="Kathmandu",
        status="DONE"
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    
    # Create some results
    for i in range(5):
        result = CleanedResult(
            job_id=job.id,
            source_id=1,
            category_id=10,
            name=f"Test Business {i+1}",
            status="PENDING"
        )
        db_session.add(result)
    
    db_session.commit()
    
    return job


@pytest.fixture
def test_job_failed(db_session: Session, test_user: User):
    """Create a test job with FAILED status"""
    # Create category
    category = db_session.query(Category).filter(Category.id == 10).first()
    if not category:
        category = Category(id=10, name="test_hotels", display_name="Test Hotels")
        db_session.add(category)
        db_session.commit()
    
    # Create job
    job = ScrapeJob(
        user_id=test_user.id,
        category_id=10,
        location="Pokhara",
        status="FAILED",
        error_message="Test error"
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    
    return job


def test_get_smtp_config_returns_none_when_not_configured():
    """Test get_smtp_config returns None when SMTP_HOST is not set"""
    with patch.dict(os.environ, {}, clear=True):
        config = get_smtp_config()
        assert config is None


def test_get_smtp_config_returns_config_when_configured():
    """Test get_smtp_config returns configuration when SMTP_HOST is set"""
    with patch.dict(os.environ, {
        "SMTP_HOST": "smtp.example.com",
        "SMTP_PORT": "587",
        "SMTP_USER": "test@example.com",
        "SMTP_PASSWORD": "test_password",
        "SMTP_FROM_EMAIL": "noreply@example.com"
    }):
        config = get_smtp_config()
        
        assert config is not None
        assert config["host"] == "smtp.example.com"
        assert config["port"] == 587
        assert config["username"] == "test@example.com"
        assert config["password"] == "test_password"
        assert config["from_email"] == "noreply@example.com"
        assert config["use_tls"] is True


def test_get_frontend_url_returns_default():
    """Test get_frontend_url returns default when not configured"""
    with patch.dict(os.environ, {}, clear=True):
        url = get_frontend_url()
        assert url == "http://localhost:5173"


def test_get_frontend_url_returns_configured_value():
    """Test get_frontend_url returns configured value"""
    with patch.dict(os.environ, {"FRONTEND_URL": "https://example.com"}):
        url = get_frontend_url()
        assert url == "https://example.com"


def test_build_success_email_contains_correct_data(test_job_done: ScrapeJob):
    """Test build_success_email contains correct subject and result count"""
    subject, html_body, text_body = build_success_email(
        test_job_done,
        "Test Hotels",
        5,
        "http://localhost:5173"
    )
    
    # Check subject
    assert "Completed" in subject
    assert test_job_done.location in subject
    
    # Check HTML body
    assert str(test_job_done.id) in html_body
    assert test_job_done.location in html_body
    assert "Test Hotels" in html_body
    assert "5" in html_body
    assert f"/jobs/{test_job_done.id}/results" in html_body
    
    # Check text body
    assert str(test_job_done.id) in text_body
    assert test_job_done.location in text_body
    assert "Test Hotels" in text_body
    assert "5" in text_body


def test_build_failure_email_contains_correct_data(test_job_failed: ScrapeJob):
    """Test build_failure_email contains correct subject and failure message"""
    subject, html_body, text_body = build_failure_email(
        test_job_failed,
        "Test Hotels",
        "http://localhost:5173"
    )
    
    # Check subject
    assert "Failed" in subject
    assert test_job_failed.location in subject
    
    # Check HTML body
    assert str(test_job_failed.id) in html_body
    assert test_job_failed.location in html_body
    assert "Test Hotels" in html_body
    assert f"/jobs/{test_job_failed.id}" in html_body
    
    # Check text body
    assert str(test_job_failed.id) in text_body
    assert test_job_failed.location in text_body
    assert "Test Hotels" in text_body


@pytest.mark.asyncio
async def test_send_email_skips_when_smtp_not_configured(db_session: Session, test_job_done: ScrapeJob):
    """Test email sending skips silently when SMTP_HOST is not set"""
    with patch.dict(os.environ, {}, clear=True):
        result = await send_job_completion_email(test_job_done, db_session)
        
        # Should return False but not raise
        assert result is False


@pytest.mark.asyncio
async def test_send_email_skips_when_user_has_no_email(db_session: Session, test_job_done: ScrapeJob):
    """Test email sending skips when user has no email"""
    # Mock the user query to return a user without email
    from models import User
    
    with patch.dict(os.environ, {"SMTP_HOST": "smtp.example.com"}):
        # Mock the user query to return None for user
        with patch.object(db_session, 'query') as mock_query:
            # Create a mock user with no email
            mock_user = MagicMock(spec=User)
            mock_user.email = None
            mock_query.return_value.filter.return_value.first.return_value = mock_user
            
            result = await send_job_completion_email(test_job_done, db_session)
            
            # Should return False but not raise
            assert result is False


@pytest.mark.asyncio
async def test_send_email_success_for_done_job(db_session: Session, test_job_done: ScrapeJob, mock_smtp_config):
    """Test email sends successfully when SMTP configured for DONE job"""
    # Get user email
    from models import User
    user = db_session.query(User).filter(User.id == test_job_done.user_id).first()
    
    with patch.dict(os.environ, {
        "SMTP_HOST": "smtp.example.com",
        "SMTP_PORT": "587",
        "SMTP_USER": "test@example.com",
        "SMTP_PASSWORD": "test_password",
        "SMTP_FROM_EMAIL": "noreply@example.com",
        "FRONTEND_URL": "http://localhost:5173"
    }):
        with patch("services.email_service.aiosmtplib.send", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = None
            
            result = await send_job_completion_email(test_job_done, db_session)
            
            # Should return True
            assert result is True
            
            # Should have called aiosmtplib.send
            assert mock_send.called
            
            # Check the message that was sent
            call_args = mock_send.call_args
            message = call_args[0][0]
            
            assert message["To"] == user.email
            assert message["From"] == "noreply@example.com"
            assert "Completed" in message["Subject"]


@pytest.mark.asyncio
async def test_send_email_success_for_failed_job(db_session: Session, test_job_failed: ScrapeJob):
    """Test email sends successfully for FAILED job"""
    # Get user email
    from models import User
    user = db_session.query(User).filter(User.id == test_job_failed.user_id).first()
    
    with patch.dict(os.environ, {
        "SMTP_HOST": "smtp.example.com",
        "SMTP_PORT": "587",
        "SMTP_USER": "test@example.com",
        "SMTP_PASSWORD": "test_password",
        "SMTP_FROM_EMAIL": "noreply@example.com",
        "FRONTEND_URL": "http://localhost:5173"
    }):
        with patch("services.email_service.aiosmtplib.send", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = None
            
            result = await send_job_completion_email(test_job_failed, db_session)
            
            # Should return True
            assert result is True
            
            # Should have called aiosmtplib.send
            assert mock_send.called
            
            # Check the message that was sent
            call_args = mock_send.call_args
            message = call_args[0][0]
            
            assert message["To"] == user.email
            assert "Failed" in message["Subject"]


@pytest.mark.asyncio
async def test_send_email_handles_smtp_error_gracefully(db_session: Session, test_job_done: ScrapeJob):
    """Test SMTP connection failure logs error but does not raise"""
    with patch.dict(os.environ, {
        "SMTP_HOST": "smtp.example.com",
        "SMTP_PORT": "587",
        "SMTP_USER": "test@example.com",
        "SMTP_PASSWORD": "test_password",
        "SMTP_FROM_EMAIL": "noreply@example.com"
    }):
        with patch("services.email_service.aiosmtplib.send", new_callable=AsyncMock) as mock_send:
            # Simulate SMTP error
            mock_send.side_effect = Exception("SMTP connection failed")
            
            # Should not raise, should return False
            result = await send_job_completion_email(test_job_done, db_session)
            
            assert result is False


@pytest.mark.asyncio
async def test_send_email_skips_for_invalid_status(db_session: Session, test_user: User):
    """Test email sending skips for invalid job status"""
    # Create job with RUNNING status
    job = ScrapeJob(
        user_id=test_user.id,
        category_id=1,
        location="Kathmandu",
        status="RUNNING"
    )
    db_session.add(job)
    db_session.commit()
    
    with patch.dict(os.environ, {"SMTP_HOST": "smtp.example.com"}):
        result = await send_job_completion_email(job, db_session)
        
        # Should return False for invalid status
        assert result is False


@pytest.mark.asyncio
async def test_email_includes_correct_frontend_link(db_session: Session, test_job_done: ScrapeJob):
    """Test email includes correct link to frontend results page"""
    with patch.dict(os.environ, {
        "SMTP_HOST": "smtp.example.com",
        "SMTP_PORT": "587",
        "SMTP_USER": "test@example.com",
        "SMTP_PASSWORD": "test_password",
        "SMTP_FROM_EMAIL": "noreply@example.com",
        "FRONTEND_URL": "https://example.com"
    }):
        with patch("services.email_service.aiosmtplib.send", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = None
            
            await send_job_completion_email(test_job_done, db_session)
            
            # Check the message content
            call_args = mock_send.call_args
            message = call_args[0][0]
            
            # Get the HTML part
            html_part = None
            for part in message.walk():
                if part.get_content_type() == "text/html":
                    html_part = part.get_payload(decode=True).decode()
                    break
            
            assert html_part is not None
            assert f"https://example.com/jobs/{test_job_done.id}/results" in html_part
