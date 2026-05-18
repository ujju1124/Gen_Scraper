"""
Trigger the 5 scale test jobs
"""
import sys
sys.path.insert(0, '/app')

from database import SessionLocal
from models.scrape_job import ScrapeJob
from tasks.scrape_task import scrape_task

db = SessionLocal()

try:
    # Get the 5 most recent QUEUED jobs
    jobs = db.query(ScrapeJob).filter(
        ScrapeJob.status == 'QUEUED'
    ).order_by(ScrapeJob.created_at.desc()).limit(5).all()
    
    print(f"Found {len(jobs)} queued jobs")
    
    for job in jobs:
        job_id = str(job.id)
        print(f"\nTriggering job {job_id}:")
        print(f"  Location: {job.location}")
        print(f"  Source IDs: {job.source_ids}")
        
        # Send to Celery
        result = scrape_task.delay(job_id)
        print(f"  ✅ Task sent to Celery: {result.id}")
    
    print(f"\n✅ All {len(jobs)} jobs triggered successfully")
    print("Monitor worker logs: docker logs gen_scraper-worker-1 --follow")
    
finally:
    db.close()
