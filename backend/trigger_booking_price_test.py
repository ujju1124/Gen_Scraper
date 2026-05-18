"""
Trigger Booking.com jobs to populate price data.
Creates 3 jobs for different cities to test price extraction.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from database import SessionLocal
from models import ScrapeJob, User, Category
from tasks.scrape_task import scrape_task
import uuid

def create_booking_jobs():
    """Create 3 Booking.com test jobs."""
    db = SessionLocal()
    
    try:
        # Get admin user
        user = db.query(User).filter(User.email == "admin@example.com").first()
        if not user:
            print("Error: Admin user not found")
            return
        
        # Get hotels category
        category = db.query(Category).filter(Category.name == "hotels").first()
        if not category:
            print("Error: hotels category not found")
            return
        
        # Get booking_com source ID
        from models import Source
        booking_source = db.query(Source).filter(Source.name == "booking_com").first()
        if not booking_source:
            print("Error: booking_com source not found")
            return
        
        # Create 3 jobs
        jobs_data = [
            {"location": "Kathmandu", "max_results": 20},
            {"location": "Pokhara", "max_results": 20},
            {"location": "Chitwan", "max_results": 15},
        ]
        
        created_jobs = []
        
        for job_data in jobs_data:
            job = ScrapeJob(
                id=uuid.uuid4(),
                user_id=user.id,
                category_id=category.id,
                location=job_data["location"],
                max_results=job_data["max_results"],
                source_ids=[booking_source.id],  # Only Booking.com
                status="PENDING"
            )
            db.add(job)
            db.flush()
            created_jobs.append(job)
            print(f"Created job {job.id} for {job.location} (max_results={job.max_results})")
        
        db.commit()
        
        # Trigger jobs
        print("\nTriggering jobs...")
        for job in created_jobs:
            scrape_task.delay(str(job.id))
            print(f"  Triggered job {job.id}")
        
        print(f"\n✅ Successfully created and triggered {len(created_jobs)} Booking.com jobs")
        print("\nTo monitor progress:")
        print("  docker logs gen_scraper-worker-1 --tail=50 -f")
        print("\nTo check results:")
        print("  docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c \"")
        print("    SELECT COUNT(*) as total, COUNT(price_min) as has_price,")
        print("           COUNT(price_min)*100/COUNT(*) as price_pct")
        print("    FROM cleaned_results cr")
        print("    JOIN sources s ON cr.source_id = s.id")
        print("    WHERE s.name = 'booking_com';\"")
        
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_booking_jobs()
