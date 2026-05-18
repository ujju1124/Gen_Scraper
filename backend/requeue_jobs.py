"""
Re-queue jobs that are marked as QUEUED in database but not in Celery queue.
Run with: docker exec gen_scraper-backend-1 python requeue_jobs.py
"""
import sys
sys.path.insert(0, '/app')

from database import SessionLocal
from models.scrape_job import ScrapeJob
from tasks.scrape_task import scrape_task

def requeue_jobs():
    db = SessionLocal()
    try:
        # Get all QUEUED jobs
        queued_jobs = db.query(ScrapeJob).filter(ScrapeJob.status == "QUEUED").all()
        
        print(f"Found {len(queued_jobs)} QUEUED jobs")
        
        requeued = 0
        for job in queued_jobs:
            try:
                # Send to Celery
                scrape_task.delay(str(job.id))
                requeued += 1
                print(f"Re-queued job {job.id} ({job.location})")
            except Exception as e:
                print(f"Failed to re-queue job {job.id}: {e}")
        
        print(f"\nSuccessfully re-queued {requeued}/{len(queued_jobs)} jobs")
        
    finally:
        db.close()

if __name__ == "__main__":
    requeue_jobs()
