"""
Cross-job merge task.

Merges records across ALL jobs from different sources so that the same
business scraped from Booking.com, Google Maps, NepalYP etc. becomes
one canonical record instead of separate duplicates.

Usage:
    # Via Celery (async)
    from tasks.merge_task import merge_all_sources
    merge_all_sources.delay()

    # Via API
    POST /api/v1/admin/merge-all-sources

    # Direct (sync, for scripts/tests)
    from tasks.merge_task import run_merge_sync
    stats = run_merge_sync()
"""

import structlog
from celery import shared_task

from database import SessionLocal
from scrapers.merger import MergingPipeline

logger = structlog.get_logger()


@shared_task(bind=True, name="tasks.merge_all_sources", max_retries=1)
def merge_all_sources(self):
    """
    Celery task: merge all records across all jobs from different sources.

    Groups every non-duplicate cleaned_result by dedup_key across all jobs,
    then runs fuzzy matching on remaining unmatched records.

    Returns dict with merge statistics.
    """
    logger.info("merge_all_sources.started")
    db = SessionLocal()
    try:
        pipeline = MergingPipeline(db)
        stats = pipeline.run_cross_job()
        logger.info("merge_all_sources.complete", **stats)
        return stats
    except Exception as exc:
        logger.error("merge_all_sources.failed", error=str(exc))
        raise self.retry(exc=exc, countdown=10)
    finally:
        db.close()


def run_merge_sync() -> dict:
    """
    Synchronous version for scripts, tests, and direct API calls.
    Returns merge statistics dict.
    """
    logger.info("merge_all_sources.sync_started")
    db = SessionLocal()
    try:
        pipeline = MergingPipeline(db)
        stats = pipeline.run_cross_job()
        logger.info("merge_all_sources.sync_complete", **stats)
        return stats
    finally:
        db.close()
