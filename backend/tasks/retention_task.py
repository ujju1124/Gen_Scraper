"""
Data retention task for auto-purging old raw_results.

This Celery task runs daily to delete raw_results older than 90 days
to prevent disk space issues in production.
"""
import structlog
from datetime import datetime, timedelta
from sqlalchemy import text
from database import SessionLocal
from config import settings

logger = structlog.get_logger()


def purge_old_raw_results(db_session=None):
    """
    Celery task to delete raw_results older than retention period.
    
    Runs daily at 02:00 AM via Celery Beat schedule.
    Deletes in batches of 1000 to avoid table locks.
    
    Args:
        db_session: Optional database session (for testing). If None, creates new session.
    
    Returns:
        dict: Summary of deletion operation with count and duration
    """
    start_time = datetime.utcnow()
    retention_days = getattr(settings, 'RAW_RESULTS_RETENTION_DAYS', 90)
    cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
    
    logger.info(
        "retention.purge_start",
        retention_days=retention_days,
        cutoff_date=cutoff_date.isoformat()
    )
    
    # Use provided session or create new one
    db = db_session or SessionLocal()
    total_deleted = 0
    batch_size = 1000
    should_close = db_session is None  # Only close if we created the session
    
    try:
        while True:
            # Delete in batches to avoid table locks
            result = db.execute(
                text("""
                    DELETE FROM raw_results
                    WHERE id IN (
                        SELECT id FROM raw_results
                        WHERE scraped_at < :cutoff_date
                        ORDER BY scraped_at
                        LIMIT :batch_size
                    )
                """),
                {"cutoff_date": cutoff_date, "batch_size": batch_size}
            )
            
            deleted_count = result.rowcount
            total_deleted += deleted_count
            
            db.commit()
            
            logger.debug(
                "retention.batch_deleted",
                batch_deleted=deleted_count,
                total_deleted=total_deleted
            )
            
            # Stop when no more records to delete
            if deleted_count < batch_size:
                break
        
        duration_seconds = (datetime.utcnow() - start_time).total_seconds()
        
        logger.info(
            "retention.purge_complete",
            total_deleted=total_deleted,
            duration_seconds=duration_seconds,
            retention_days=retention_days
        )
        
        return {
            "success": True,
            "deleted_count": total_deleted,
            "duration_seconds": duration_seconds,
            "retention_days": retention_days
        }
        
    except Exception as e:
        db.rollback()
        
        logger.error(
            "retention.purge_failed",
            error=str(e),
            error_type=type(e).__name__,
            total_deleted=total_deleted
        )
        
        # Do not crash Beat scheduler - log and continue
        return {
            "success": False,
            "error": str(e),
            "deleted_count": total_deleted
        }
        
    finally:
        if should_close:
            db.close()
