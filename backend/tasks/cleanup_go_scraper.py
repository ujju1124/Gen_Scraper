"""
Periodic cleanup task for Go scraper queues.
Removes stuck jobs that have been pending/working for too long.
"""

import requests
import structlog
from datetime import datetime, timedelta
from celery import shared_task

logger = structlog.get_logger(__name__)


@shared_task(name="tasks.cleanup_go_scraper_queue")
def cleanup_go_scraper_queue():
    """
    Clean up stuck jobs in Go scraper queues.
    
    Removes jobs that have been in 'pending' or 'working' status
    for more than 15 minutes. Failed jobs are removed immediately.
    These jobs are likely stuck and will never complete, blocking
    the queue for new jobs.
    
    Runs every 5 minutes via Celery Beat.
    
    Note: With batched parallel submission and instance restarts,
    jobs should never stay pending more than a few seconds. The
    15-minute threshold provides generous buffer for legitimate jobs.
    """
    go_scraper_urls = [
        "http://go_scraper_1:8080",
        "http://go_scraper_2:8080",
        "http://go_scraper_3:8080",
        "http://go_scraper_4:8080",
    ]
    
    total_deleted = 0
    total_checked = 0
    
    for url in go_scraper_urls:
        try:
            # Get all jobs from this Go scraper instance
            response = requests.get(f"{url}/api/v1/jobs", timeout=5)
            response.raise_for_status()
            
            data = response.json()
            
            # Handle both response formats: array or {"value": array}
            if isinstance(data, list):
                jobs = data
            elif isinstance(data, dict):
                jobs = data.get("value", [])
            else:
                logger.warning(
                    "go_scraper.cleanup_invalid_response",
                    instance=url,
                    message="Invalid JSON response format"
                )
                continue
                
            total_checked += len(jobs)
            
            if not jobs:
                logger.info(
                    "go_scraper.cleanup_empty",
                    instance=url,
                    message="No jobs in queue"
                )
                continue
            
            # Find stuck jobs (pending/working for > 15 minutes, or failed)
            cutoff_time = datetime.utcnow() - timedelta(minutes=15)
            stuck_jobs = []
            
            for job in jobs:
                try:
                    # Parse job date (format: "2026-05-29T16:36:42Z")
                    job_date_str = job.get("Date", "")
                    status = job.get("Status", "")
                    
                    # Failed jobs: delete immediately (no timeout)
                    if status == "failed":
                        stuck_jobs.append(job)
                        continue
                    
                    # Pending/working jobs: delete if older than 5 minutes
                    if job_date_str and status in ["pending", "working"]:
                        # Remove 'Z' and parse
                        job_date = datetime.fromisoformat(job_date_str.replace("Z", ""))
                        
                        # Check if stuck
                        if job_date < cutoff_time:
                            stuck_jobs.append(job)
                except Exception as e:
                    logger.warning(
                        "go_scraper.cleanup_parse_error",
                        instance=url,
                        job_id=job.get("ID"),
                        error=str(e)
                    )
            
            # Delete stuck jobs
            for job in stuck_jobs:
                try:
                    job_id = job.get("ID")
                    job_name = job.get("Name", "unknown")
                    job_status = job.get("Status", "unknown")
                    job_age = datetime.utcnow() - datetime.fromisoformat(
                        job.get("Date", "").replace("Z", "")
                    )
                    
                    # Try to delete (Go scraper may not support DELETE)
                    delete_response = requests.delete(
                        f"{url}/api/v1/jobs/{job_id}",
                        timeout=5
                    )
                    
                    if delete_response.status_code in [200, 204, 404]:
                        total_deleted += 1
                        logger.info(
                            "go_scraper.cleanup_deleted",
                            instance=url,
                            job_id=job_id,
                            job_name=job_name,
                            status=job_status,
                            age_minutes=int(job_age.total_seconds() / 60)
                        )
                    else:
                        logger.warning(
                            "go_scraper.cleanup_delete_failed",
                            instance=url,
                            job_id=job_id,
                            status_code=delete_response.status_code
                        )
                
                except Exception as e:
                    logger.error(
                        "go_scraper.cleanup_delete_error",
                        instance=url,
                        job_id=job.get("ID"),
                        error=str(e)
                    )
        
        except requests.exceptions.RequestException as e:
            logger.error(
                "go_scraper.cleanup_connection_error",
                instance=url,
                error=str(e)
            )
        except Exception as e:
            logger.error(
                "go_scraper.cleanup_unexpected_error",
                instance=url,
                error=str(e)
            )
    
    logger.info(
        "go_scraper.cleanup_complete",
        total_checked=total_checked,
        total_deleted=total_deleted,
        instances=len(go_scraper_urls)
    )
    
    return {
        "total_checked": total_checked,
        "total_deleted": total_deleted,
        "instances": len(go_scraper_urls)
    }
