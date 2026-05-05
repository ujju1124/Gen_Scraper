"""
Celery tasks for web scraping.
Contains both Phase 1 mock task and Phase 2 real orchestrator integration.
Phase 4B: Added geocoding integration after cleaning pipeline.
"""
import asyncio
import random
import time
import hashlib
import uuid
from datetime import datetime
from celery import Celery
import structlog
from sqlalchemy.orm import Session

from config import settings
from database import SessionLocal
from models import ScrapeJob, RawResult, CleanedResult
from scrapers.orchestrator import ScraperOrchestrator
from scrapers.cleaner import CleaningPipeline
from services.geocoding_service import geocoding_service
from services.email_service import send_job_completion_email

# Configure structlog
logger = structlog.get_logger()

# Create Celery app
celery_app = Celery(
    "scraper",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    broker_connection_retry_on_startup=True,
)


@celery_app.task(name="tasks.scrape_task")
def scrape_task(job_id: str):
    """
    Main scrape task entry point.
    
    Routes to either mock implementation (Phase 1) or real orchestrator (Phase 2)
    based on MOCK_MODE environment variable.
    
    Args:
        job_id: UUID string of the scrape job
    """
    if settings.MOCK_MODE:
        logger.info("task.routing_to_mock", job_id=job_id, mock_mode=True)
        return mock_scrape_task_impl(job_id)
    else:
        logger.info("task.routing_to_real", job_id=job_id, mock_mode=False)
        return real_scrape_task_impl(job_id)


def mock_scrape_task_impl(job_id: str):
    """
    Fake scraper task for Phase 1 testing.
    
    - Sleeps random 3-8 seconds
    - Generates exactly 10 synthetic records
    - Inserts into raw_results and cleaned_results
    - Updates job status: QUEUED → RUNNING → DONE/FAILED
    
    Args:
        job_id: UUID string of the scrape job
    """
    # Convert job_id string to UUID object
    job_uuid = uuid.UUID(job_id)
    
    db = SessionLocal()
    
    try:
        # Load job from database
        job = db.query(ScrapeJob).filter(ScrapeJob.id == job_uuid).first()
        
        if not job:
            logger.error("job.not_found", job_id=job_id)
            return
        
        # Set status to RUNNING
        job.status = "RUNNING"
        job.started_at = datetime.utcnow()
        db.commit()
        logger.info("job.started", job_id=job_id, location=job.location, category_id=job.category_id)
        
        # Sleep random 3-8 seconds
        sleep_duration = random.randint(3, 8)
        time.sleep(sleep_duration)
        
        # Generate exactly 10 synthetic records
        fake_names = [
            "Hotel Himalaya", "Yak & Yeti Hotel", "Dwarika's Hotel",
            "Hyatt Regency Kathmandu", "Radisson Hotel", "Hotel Shanker",
            "Soaltee Crowne Plaza", "Hotel Annapurna", "Gokarna Forest Resort",
            "The Everest Hotel"
        ]
        
        fake_cities = ["Kathmandu", "Pokhara", "Lalitpur", "Bhaktapur", "Chitwan"]
        
        for i in range(10):
            name = fake_names[i]
            city = random.choice(fake_cities)
            
            # Generate dedup_key: SHA-256(lowercase(name) + lowercase(city))
            dedup_string = f"{name.lower()}{city.lower()}"
            dedup_key = hashlib.sha256(dedup_string.encode()).hexdigest()
            
            # Generate synthetic raw data
            raw_data = {
                "name": name,
                "city": city,
                "rating": round(random.uniform(7.0, 9.5), 1),
                "price": random.randint(2000, 8000),
                "address": f"{random.randint(1, 100)} Main Street, {city}"
            }
            
            # Insert into raw_results (source_id=1 is the seeded placeholder)
            raw_result = RawResult(
                job_id=job_uuid,
                source_id=1,
                raw_data=raw_data
            )
            db.add(raw_result)
            
            # Calculate data completeness (percentage of non-null fields)
            # For this fake data, we'll use a random score between 60-95%
            data_completeness = round(random.uniform(60.0, 95.0), 2)
            
            # Insert into cleaned_results
            cleaned_result = CleanedResult(
                job_id=job_uuid,
                source_id=1,
                category_id=job.category_id,
                dedup_key=dedup_key,
                name=name,
                city=city,
                address=raw_data["address"],
                rating_overall=raw_data["rating"],
                price_min=raw_data["price"],
                currency="NPR",
                data_completeness=data_completeness,
                status="PENDING"
            )
            db.add(cleaned_result)
        
        db.commit()
        
        # Set status to DONE
        job.status = "DONE"
        job.completed_at = datetime.utcnow()
        db.commit()
        
        logger.info("job.done", job_id=job_id, result_count=10, duration_seconds=sleep_duration)
        
        # Send email notification (never crash on email failure)
        try:
            asyncio.run(send_job_completion_email(job, db))
        except Exception as e:
            logger.error("email_notification_failed", job_id=job_id, error=str(e))
        
    except Exception as e:
        # Set status to FAILED
        try:
            job = db.query(ScrapeJob).filter(ScrapeJob.id == job_uuid).first()
            if job:
                job.status = "FAILED"
                job.error_message = str(e)
                job.completed_at = datetime.utcnow()
                db.commit()
                
                # Send email notification for failure (never crash on email failure)
                try:
                    asyncio.run(send_job_completion_email(job, db))
                except Exception as email_error:
                    logger.error("email_notification_failed", job_id=job_id, error=str(email_error))
        except Exception as commit_error:
            logger.error("job.failed_to_update_status", job_id=job_id, error=str(commit_error))
        
        logger.error("job.failed", job_id=job_id, error=str(e), exc_info=True)
        raise
        
    finally:
        db.close()


def real_scrape_task_impl(job_id: str):
    """
    Real scraper task implementation for Phase 2.
    
    Uses ScraperOrchestrator to run scrapers with domain grouping and concurrency control,
    then runs CleaningPipeline to process results through 7-step cleaning process.
    Phase 4B: Added geocoding step after cleaning to add coordinates to results.
    Phase 6A: Added MergingPipeline step between cleaning and geocoding (Clean → Merge → Geocode).
    
    Updates job status: QUEUED → RUNNING → DONE/FAILED
    Saves failed_source_ids to database for retry logic.
    
    Args:
        job_id: UUID string of the scrape job
    """
    # Convert job_id string to UUID object
    job_uuid = uuid.UUID(job_id)
    
    db = SessionLocal()
    
    try:
        # Load job from database
        job = db.query(ScrapeJob).filter(ScrapeJob.id == job_uuid).first()
        
        if not job:
            logger.error("job.not_found", job_id=job_id)
            return
        
        # Set status to RUNNING
        job.status = "RUNNING"
        job.started_at = datetime.utcnow()
        db.commit()
        logger.info("job.started", job_id=job_id, location=job.location, category_id=job.category_id)
        
        # Run orchestrator (async)
        orchestrator = ScraperOrchestrator()
        raw_results, failed_source_ids = asyncio.run(
            orchestrator.run_async(db, str(job_uuid))
        )
        
        logger.info(
            "job.orchestrator_complete",
            job_id=job_id,
            raw_result_count=len(raw_results),
            failed_sources=len(failed_source_ids)
        )
        
        # Run cleaning pipeline for each source's results
        total_cleaned = 0
        
        # Group results by source_id
        results_by_source = {}
        for result in raw_results:
            source_id = result.get("source_id", 1)  # Default to 1 if not specified
            if source_id not in results_by_source:
                results_by_source[source_id] = []
            results_by_source[source_id].append(result)
        
        # Process each source's results through cleaning pipeline
        for source_id, source_results in results_by_source.items():
            cleaner = CleaningPipeline(db)
            cleaned_results = cleaner.process(
                source_results,
                str(job_uuid),
                source_id,
                job.category_id
            )
            total_cleaned += len(cleaned_results)
        
        logger.info(
            "job.cleaning_complete",
            job_id=job_id,
            cleaned_result_count=total_cleaned
        )
        
        # Phase 6A: Merge results from multiple sources (Clean → Merge → Geocode)
        if total_cleaned > 0:
            try:
                from scrapers.merger import MergingPipeline
                merge_stats = MergingPipeline(db).run(str(job_uuid))
                logger.info(
                    "job.merging_complete",
                    job_id=job_id,
                    merged_groups=merge_stats["merged_groups"],
                    total_records_processed=merge_stats["total_records_processed"]
                )
            except Exception as merge_error:
                logger.warning(
                    "job.merging_failed",
                    job_id=job_id,
                    error=str(merge_error),
                    exc_info=True
                )
                # Do NOT re-raise — job continues to DONE
        
        # Phase 4B: Geocode cleaned results
        if settings.GEOCODING_ENABLED and total_cleaned > 0:
            try:
                geocoded_count = asyncio.run(
                    geocode_job_results(db, str(job_uuid))
                )
                logger.info(
                    "job.geocoding_complete",
                    job_id=job_id,
                    geocoded_count=geocoded_count
                )
            except Exception as geocoding_error:
                # Log error but don't fail the job
                logger.warning(
                    "job.geocoding_failed",
                    job_id=job_id,
                    error=str(geocoding_error),
                    exc_info=True
                )
        
        # Update job with results
        job.status = "DONE"
        job.completed_at = datetime.utcnow()
        job.failed_source_ids = failed_source_ids if failed_source_ids else None
        db.commit()
        
        logger.info(
            "job.done",
            job_id=job_id,
            result_count=total_cleaned,
            failed_sources=len(failed_source_ids)
        )
        
        # Send email notification (never crash on email failure)
        try:
            asyncio.run(send_job_completion_email(job, db))
        except Exception as e:
            logger.error("email_notification_failed", job_id=job_id, error=str(e))
        
    except Exception as e:
        # Set status to FAILED
        try:
            job = db.query(ScrapeJob).filter(ScrapeJob.id == job_uuid).first()
            if job:
                job.status = "FAILED"
                job.error_message = str(e)
                job.completed_at = datetime.utcnow()
                db.commit()
                
                # Send email notification for failure (never crash on email failure)
                try:
                    asyncio.run(send_job_completion_email(job, db))
                except Exception as email_error:
                    logger.error("email_notification_failed", job_id=job_id, error=str(email_error))
        except Exception as commit_error:
            logger.error("job.failed_to_update_status", job_id=job_id, error=str(commit_error))
        
        logger.error("job.failed", job_id=job_id, error=str(e), exc_info=True)
        raise
        
    finally:
        db.close()


async def geocode_job_results(db: Session, job_id: str, timeout_seconds: int = 300) -> int:
    """
    Geocode all cleaned results for a job.
    
    Extracts addresses from cleaned_results, calls geocoding service in batch,
    and updates results with latitude/longitude coordinates.
    
    Args:
        db: SQLAlchemy database session
        job_id: UUID string of the scrape job
        timeout_seconds: Maximum time to spend geocoding (default: 5 minutes)
        
    Returns:
        Number of results successfully geocoded
        
    Raises:
        asyncio.TimeoutError: If geocoding exceeds timeout
    """
    start_time = time.time()
    geocoded_count = 0
    
    try:
        # Convert job_id to UUID
        job_uuid = uuid.UUID(job_id)
        
        # Load cleaned results for this job that need geocoding
        results = db.query(CleanedResult).filter(
            CleanedResult.job_id == job_uuid,
            CleanedResult.latitude.is_(None),  # Only geocode results without coordinates
            CleanedResult.address.isnot(None),  # Must have an address
            CleanedResult.city.isnot(None)      # Must have a city
        ).all()
        
        if not results:
            logger.info(
                "geocoding.no_results_to_geocode",
                job_id=job_id
            )
            return 0
        
        logger.info(
            "geocoding.started",
            job_id=job_id,
            result_count=len(results)
        )
        
        # Prepare addresses for batch geocoding
        addresses = []
        result_map = {}  # Map index to result object
        
        for idx, result in enumerate(results):
            # Use street_address if available, otherwise use full address
            address = result.street_address or result.address or result.name
            city = result.city or "Kathmandu"  # Default to Kathmandu if city missing
            country = result.country or "Nepal"
            
            addresses.append({
                "address": address,
                "city": city,
                "country": country
            })
            result_map[idx] = result
        
        # Geocode in batch with timeout
        try:
            coords_list = await asyncio.wait_for(
                geocoding_service.geocode_batch(addresses, use_cache=True),
                timeout=timeout_seconds
            )
        except asyncio.TimeoutError:
            logger.error(
                "geocoding.timeout",
                job_id=job_id,
                timeout_seconds=timeout_seconds,
                processed_count=geocoded_count
            )
            raise
        
        # Update results with coordinates
        for idx, coords in enumerate(coords_list):
            result = result_map[idx]
            
            if coords:
                result.latitude = coords.lat
                result.longitude = coords.lng
                geocoded_count += 1
                
                logger.debug(
                    "geocoding.result_updated",
                    job_id=job_id,
                    result_id=str(result.id),
                    address=addresses[idx]["address"],
                    city=addresses[idx]["city"],
                    lat=coords.lat,
                    lng=coords.lng,
                    source=coords.source
                )
            else:
                logger.debug(
                    "geocoding.result_failed",
                    job_id=job_id,
                    result_id=str(result.id),
                    address=addresses[idx]["address"],
                    city=addresses[idx]["city"]
                )
        
        # Commit all updates
        db.commit()
        
        elapsed_time = time.time() - start_time
        success_rate = (geocoded_count / len(results) * 100) if results else 0
        
        logger.info(
            "geocoding.completed",
            job_id=job_id,
            total_results=len(results),
            geocoded_count=geocoded_count,
            success_rate=f"{success_rate:.1f}%",
            elapsed_seconds=f"{elapsed_time:.2f}"
        )
        
        return geocoded_count
        
    except asyncio.TimeoutError:
        # Re-raise timeout error
        raise
    except Exception as e:
        logger.error(
            "geocoding.error",
            job_id=job_id,
            error=str(e),
            exc_info=True
        )
        # Rollback any partial updates
        db.rollback()
        raise
