"""
Go Scraper Queue Cleanup Task

Automatically cleans up stuck jobs in the Go scraper queue to prevent blockage.
Runs periodically via Celery Beat.
"""

from datetime import datetime, timezone
import httpx
import structlog
from celery import shared_task

from config import settings

logger = structlog.get_logger()


@shared_task(name="tasks.cleanup_go_scraper_queue")
def cleanup_go_scraper_queue():
    """
    Clean up stuck Go scraper jobs.
    
    Deletes jobs that have been in 'working' status for more than 15 minutes.
    This prevents one stuck job from blocking the entire queue.
    
    Runs every 5 minutes via Celery Beat.
    """
    if not settings.GO_SCRAPER_ENABLED:
        logger.debug("cleanup.skipped", reason="go_scraper_disabled")
        return
    
    try:
        # Get all jobs from Go scraper
        response = httpx.get(
            f"{settings.GO_SCRAPER_URL}/api/v1/jobs",
            timeout=10
        )
        
        if response.status_code != 200:
            logger.error(
                "cleanup.api_error",
                status_code=response.status_code,
                body=response.text[:200]
            )
            return
        
        jobs = response.json()
        
        if not jobs:
            logger.debug("cleanup.no_jobs")
            return
        
        # Check for stuck jobs
        now = datetime.now(timezone.utc)
        stuck_jobs = []
        
        for job in jobs:
            if job.get('Status') != 'working' and job.get('status') != 'working':
                continue
            
            # Parse job date
            date_str = job.get('Date') or job.get('date')
            if not date_str:
                continue
            
            try:
                # Handle both formats: with and without 'Z'
                if date_str.endswith('Z'):
                    job_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                else:
                    job_date = datetime.fromisoformat(date_str)
                
                # Make timezone-aware if needed
                if job_date.tzinfo is None:
                    job_date = job_date.replace(tzinfo=timezone.utc)
                
                elapsed_seconds = (now - job_date).total_seconds()
                
                # Consider stuck if running for more than 15 minutes (900 seconds)
                if elapsed_seconds > 900:
                    stuck_jobs.append({
                        'id': job.get('ID') or job.get('id'),
                        'name': job.get('Name') or job.get('name'),
                        'elapsed_seconds': elapsed_seconds,
                        'elapsed_minutes': round(elapsed_seconds / 60, 1)
                    })
            
            except (ValueError, TypeError) as e:
                logger.warning(
                    "cleanup.date_parse_error",
                    job_id=job.get('ID') or job.get('id'),
                    date_str=date_str,
                    error=str(e)
                )
                continue
        
        if not stuck_jobs:
            logger.debug(
                "cleanup.no_stuck_jobs",
                total_jobs=len(jobs),
                working_jobs=sum(1 for j in jobs if j.get('Status') == 'working' or j.get('status') == 'working')
            )
            return
        
        # Delete stuck jobs
        deleted_count = 0
        for stuck_job in stuck_jobs:
            job_id = stuck_job['id']
            
            logger.warning(
                "cleanup.deleting_stuck_job",
                job_id=job_id,
                job_name=stuck_job['name'],
                elapsed_minutes=stuck_job['elapsed_minutes']
            )
            
            try:
                delete_response = httpx.delete(
                    f"{settings.GO_SCRAPER_URL}/api/v1/jobs/{job_id}",
                    timeout=10
                )
                
                if delete_response.status_code == 200:
                    deleted_count += 1
                    logger.info(
                        "cleanup.job_deleted",
                        job_id=job_id,
                        elapsed_minutes=stuck_job['elapsed_minutes']
                    )
                else:
                    logger.error(
                        "cleanup.delete_failed",
                        job_id=job_id,
                        status_code=delete_response.status_code
                    )
            
            except Exception as e:
                logger.error(
                    "cleanup.delete_error",
                    job_id=job_id,
                    error=str(e)
                )
        
        if deleted_count > 0:
            logger.warning(
                "cleanup.completed",
                deleted_count=deleted_count,
                total_stuck=len(stuck_jobs)
            )
    
    except httpx.ConnectError:
        logger.warning(
            "cleanup.connection_failed",
            url=settings.GO_SCRAPER_URL,
            message="Go scraper not reachable"
        )
    
    except Exception as e:
        logger.error(
            "cleanup.unexpected_error",
            error=str(e),
            exc_info=True
        )


@shared_task(name="tasks.get_go_scraper_queue_status")
def get_go_scraper_queue_status():
    """
    Get Go scraper queue status for monitoring.
    
    Returns:
        dict: Queue status with pending, working, and completed job counts
    """
    if not settings.GO_SCRAPER_ENABLED:
        return {
            "enabled": False,
            "message": "Go scraper is disabled"
        }
    
    try:
        response = httpx.get(
            f"{settings.GO_SCRAPER_URL}/api/v1/jobs",
            timeout=10
        )
        
        if response.status_code != 200:
            return {
                "error": "Failed to fetch jobs",
                "status_code": response.status_code
            }
        
        jobs = response.json()
        
        pending = [j for j in jobs if j.get('Status') == 'pending' or j.get('status') == 'pending']
        working = [j for j in jobs if j.get('Status') == 'working' or j.get('status') == 'working']
        ok = [j for j in jobs if j.get('Status') == 'ok' or j.get('status') == 'ok']
        failed = [j for j in jobs if j.get('Status') == 'failed' or j.get('status') == 'failed']
        
        return {
            "enabled": True,
            "total_jobs": len(jobs),
            "pending": len(pending),
            "working": len(working),
            "completed": len(ok),
            "failed": len(failed),
            "pending_jobs": [
                {
                    "id": j.get('ID') or j.get('id'),
                    "name": j.get('Name') or j.get('name')
                }
                for j in pending[:5]  # First 5 only
            ],
            "working_jobs": [
                {
                    "id": j.get('ID') or j.get('id'),
                    "name": j.get('Name') or j.get('name')
                }
                for j in working
            ]
        }
    
    except Exception as e:
        logger.error("queue_status.error", error=str(e))
        return {
            "error": str(e)
        }
