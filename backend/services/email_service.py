"""
Email Service
Handles sending email notifications for job completion.
"""
import os
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import aiosmtplib
from sqlalchemy.orm import Session

from models import ScrapeJob, Category

logger = logging.getLogger(__name__)


def get_smtp_config():
    """
    Get SMTP configuration from environment variables.
    Returns None if SMTP_HOST is not configured.
    """
    smtp_host = os.getenv("SMTP_HOST")
    
    if not smtp_host:
        return None
    
    return {
        "host": smtp_host,
        "port": int(os.getenv("SMTP_PORT", "587")),
        "username": os.getenv("SMTP_USER"),
        "password": os.getenv("SMTP_PASSWORD"),
        "from_email": os.getenv("SMTP_FROM_EMAIL", "noreply@example.com"),
        "use_tls": True
    }


def get_frontend_url():
    """Get frontend URL from environment variables."""
    return os.getenv("FRONTEND_URL", "http://localhost:5173")


def build_success_email(job: ScrapeJob, category_name: str, result_count: int, frontend_url: str):
    """
    Build success email content for completed job.
    
    Args:
        job: ScrapeJob instance
        category_name: Name of the category
        result_count: Number of results scraped
        frontend_url: Base URL of the frontend
    
    Returns:
        tuple: (subject, html_body, text_body)
    """
    subject = f"Scraping Job Completed - {job.location}"
    
    results_url = f"{frontend_url}/jobs/{job.id}/results"
    
    html_body = f"""
    <html>
      <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <h2 style="color: #10b981;">✓ Scraping Job Completed Successfully</h2>
        
        <p>Your scraping job has finished processing.</p>
        
        <table style="border-collapse: collapse; margin: 20px 0;">
          <tr>
            <td style="padding: 8px; font-weight: bold;">Job ID:</td>
            <td style="padding: 8px;">{job.id}</td>
          </tr>
          <tr>
            <td style="padding: 8px; font-weight: bold;">Location:</td>
            <td style="padding: 8px;">{job.location}</td>
          </tr>
          <tr>
            <td style="padding: 8px; font-weight: bold;">Category:</td>
            <td style="padding: 8px;">{category_name}</td>
          </tr>
          <tr>
            <td style="padding: 8px; font-weight: bold;">Results Found:</td>
            <td style="padding: 8px;">{result_count}</td>
          </tr>
        </table>
        
        <p>
          <a href="{results_url}" 
             style="display: inline-block; padding: 12px 24px; background-color: #3b82f6; 
                    color: white; text-decoration: none; border-radius: 6px; font-weight: bold;">
            View Results
          </a>
        </p>
        
        <p style="color: #666; font-size: 14px; margin-top: 30px;">
          This is an automated notification from Web Scraping Portal.
        </p>
      </body>
    </html>
    """
    
    text_body = f"""
Scraping Job Completed Successfully

Your scraping job has finished processing.

Job ID: {job.id}
Location: {job.location}
Category: {category_name}
Results Found: {result_count}

View your results here: {results_url}

---
This is an automated notification from Web Scraping Portal.
    """
    
    return subject, html_body, text_body


def build_failure_email(job: ScrapeJob, category_name: str, frontend_url: str):
    """
    Build failure email content for failed job.
    
    Args:
        job: ScrapeJob instance
        category_name: Name of the category
        frontend_url: Base URL of the frontend
    
    Returns:
        tuple: (subject, html_body, text_body)
    """
    subject = f"Scraping Job Failed - {job.location}"
    
    job_url = f"{frontend_url}/jobs/{job.id}"
    
    html_body = f"""
    <html>
      <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <h2 style="color: #ef4444;">✗ Scraping Job Failed</h2>
        
        <p>Unfortunately, your scraping job encountered an error and could not complete.</p>
        
        <table style="border-collapse: collapse; margin: 20px 0;">
          <tr>
            <td style="padding: 8px; font-weight: bold;">Job ID:</td>
            <td style="padding: 8px;">{job.id}</td>
          </tr>
          <tr>
            <td style="padding: 8px; font-weight: bold;">Location:</td>
            <td style="padding: 8px;">{job.location}</td>
          </tr>
          <tr>
            <td style="padding: 8px; font-weight: bold;">Category:</td>
            <td style="padding: 8px;">{category_name}</td>
          </tr>
        </table>
        
        <p>
          <a href="{job_url}" 
             style="display: inline-block; padding: 12px 24px; background-color: #3b82f6; 
                    color: white; text-decoration: none; border-radius: 6px; font-weight: bold;">
            View Job Details
          </a>
        </p>
        
        <p style="color: #666; font-size: 14px; margin-top: 30px;">
          This is an automated notification from Web Scraping Portal.
        </p>
      </body>
    </html>
    """
    
    text_body = f"""
Scraping Job Failed

Unfortunately, your scraping job encountered an error and could not complete.

Job ID: {job.id}
Location: {job.location}
Category: {category_name}

View job details here: {job_url}

---
This is an automated notification from Web Scraping Portal.
    """
    
    return subject, html_body, text_body


async def send_job_completion_email(job: ScrapeJob, db: Session):
    """
    Send email notification when a scraping job completes (DONE or FAILED).
    
    This function is designed to NEVER crash or raise exceptions.
    All errors are logged but not propagated.
    
    Args:
        job: ScrapeJob instance with status DONE or FAILED
        db: Database session for querying related data
    
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    # Bind job_id to logger for all log messages in this function
    log = logger
    job_id = str(job.id) if job else "unknown"
    
    try:
        # Check if SMTP is configured
        smtp_config = get_smtp_config()
        
        if not smtp_config:
            log.info(f"email_notification_skipped reason=smtp_not_configured job_id={job_id}")
            return False
        
        # Get user (ensure it's loaded from DB)
        from models import User
        user = db.query(User).filter(User.id == job.user_id).first()
        
        if not user or not user.email:
            log.warning(f"email_notification_skipped reason=no_user_email job_id={job_id}")
            return False
        
        # Get category name
        category = db.query(Category).filter(Category.id == job.category_id).first()
        category_name = category.display_name if category else "Unknown"
        
        # Get frontend URL
        frontend_url = get_frontend_url()
        
        # Build email content based on job status
        if job.status == "DONE":
            # Count results for this job
            from models import CleanedResult
            result_count = db.query(CleanedResult).filter(
                CleanedResult.job_id == job.id
            ).count()
            
            subject, html_body, text_body = build_success_email(
                job, category_name, result_count, frontend_url
            )
        elif job.status == "FAILED":
            subject, html_body, text_body = build_failure_email(
                job, category_name, frontend_url
            )
        else:
            log.warning(f"email_notification_skipped reason=invalid_job_status job_id={job_id} status={job.status}")
            return False
        
        # Create email message
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = smtp_config["from_email"]
        message["To"] = user.email
        
        # Attach both plain text and HTML versions
        part1 = MIMEText(text_body, "plain")
        part2 = MIMEText(html_body, "html")
        message.attach(part1)
        message.attach(part2)
        
        # Send email
        await aiosmtplib.send(
            message,
            hostname=smtp_config["host"],
            port=smtp_config["port"],
            username=smtp_config["username"],
            password=smtp_config["password"],
            use_tls=smtp_config["use_tls"]
        )
        
        log.info(f"email_notification_sent job_id={job_id} recipient={user.email} status={job.status}")
        
        return True
        
    except Exception as e:
        # Log error but NEVER raise - email failure must not affect job completion
        log.error(f"email_notification_failed job_id={job_id} error={str(e)} error_type={type(e).__name__}")
        return False
