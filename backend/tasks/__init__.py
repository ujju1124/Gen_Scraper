"""
Tasks package - imports all Celery tasks

Note: scrape_task function is not imported here to avoid shadowing
the tasks.scrape_task module name (needed for Celery CLI).
Access it via: from tasks.scrape_task import scrape_task
"""

# Import the celery app and other tasks
from tasks.scrape_task import celery_app, app
from tasks.merge_task import merge_all_sources
from tasks.retention_task import purge_old_raw_results
from tasks.cleanup_go_scraper import cleanup_go_scraper_queue

__all__ = [
    "celery_app",
    "app",
    "merge_all_sources", 
    "purge_old_raw_results",
    "cleanup_go_scraper_queue",
]
