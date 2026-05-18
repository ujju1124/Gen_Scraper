"""
Trigger a test NepalYP scrape job.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy.orm import Session
from database import SessionLocal
from models.scrape_job import ScrapeJob
from tasks.scrape_task import scrape_task
import structlog

logger = structlog.get_logger()

def create_and_trigger_nepalyp_job():
    """Create a test job for NepalYP and trigger it."""
    db: Session = SessionLocal()
    
    try:
        # Create job for nepalyp (source_id=5)
        job = ScrapeJob(
            user_id=1,  # admin user
            category_id=1,  # hotels
            source_ids=[5],  # nepalyp
            location="Kathmandu",
            max_results=5,  # Small test
            status="pending"
        )
        
        db.add(job)
        db.commit()
        db.refresh(job)
        
        logger.info(
            "nepalyp_test.job_created",
            job_id=job.id,
            source_ids=job.source_ids,
            location=job.location,
            max_results=job.max_results
        )
        
        # Trigger the job - pass job.id as string
        scrape_task.delay(str(job.id))
        
        logger.info("nepalyp_test.job_triggered", job_id=job.id)
        print(f"✓ NepalYP test job created and triggered: job_id={job.id}")
        
    except Exception as e:
        logger.error("nepalyp_test.error", error=str(e))
        print(f"✗ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_and_trigger_nepalyp_job()
