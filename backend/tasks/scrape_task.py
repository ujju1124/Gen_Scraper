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


def format_eta(elapsed_seconds: float, current_percentage: int, total_percentage: int = 100) -> str:
    """
    Calculate and format estimated time remaining.
    
    Args:
        elapsed_seconds: Time elapsed so far
        current_percentage: Current progress percentage (0-100)
        total_percentage: Total progress when complete (default 100)
    
    Returns:
        Formatted ETA string like "2m 30s" or "45s" or "Calculating..."
    """
    if current_percentage <= 0:
        return "Calculating..."
    
    # Calculate average time per percentage point
    time_per_percent = elapsed_seconds / current_percentage
    
    # Calculate remaining percentage
    remaining_percent = total_percentage - current_percentage
    
    # Calculate ETA in seconds
    eta_seconds = time_per_percent * remaining_percent
    
    # Format as human-readable string
    if eta_seconds < 60:
        return f"{int(eta_seconds)}s"
    elif eta_seconds < 3600:
        minutes = int(eta_seconds / 60)
        seconds = int(eta_seconds % 60)
        return f"{minutes}m {seconds}s"
    else:
        hours = int(eta_seconds / 3600)
        minutes = int((eta_seconds % 3600) / 60)
        return f"{hours}h {minutes}m"


# Create Celery app
celery_app = Celery(
    "scraper",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

# Alias for Celery CLI compatibility
app = celery_app

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    broker_connection_retry_on_startup=True,
    beat_schedule={
        'cleanup-go-scraper-queue': {
            'task': 'tasks.cleanup_go_scraper_queue',
            'schedule': 300.0,  # Every 5 minutes (300 seconds)
        },
    },
)


@celery_app.task(name="tasks.scrape_task", time_limit=5400, soft_time_limit=5100)
def scrape_task(job_id: str):
    """
    Main scrape task entry point.
    
    Routes to either mock implementation (Phase 1) or real orchestrator (Phase 2)
    based on MOCK_MODE environment variable.
    
    Time limits:
    - Soft limit: 5100 seconds (85 minutes) - raises SoftTimeLimitExceeded
    - Hard limit: 5400 seconds (90 minutes) - kills the task
    
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


async def track_go_scraper_progress(job_id: str, db: Session, max_results: int, start_time: float):
    """
    Poll Go scraper API for real-time progress during scraping phase.
    
    Queries all Go scraper instances to get current job status and counts results
    by downloading CSV files to determine actual scraped count.
    
    Args:
        job_id: Job UUID string
        db: Database session (NOTE: We create a fresh session inside for thread safety)
        max_results: Maximum results requested (for calculating percentage)
        start_time: Job start timestamp (for calculating ETA)
    """
    import csv
    import io
    
    job_uuid = uuid.UUID(job_id)
    
    # Go scraper instances
    instances = [
        "http://go_scraper_1:8080",
        "http://go_scraper_2:8080",
        "http://go_scraper_3:8080",
        "http://go_scraper_4:8080",
    ]
    
    logger.info("progress_tracker.started", job_id=job_id)
    
    try:
        import httpx
        async with httpx.AsyncClient(timeout=10) as http_client:
            # Query all instances for jobs
            total_scraped = 0
            active_jobs = []
            
            for instance in instances:
                try:
                    # Get list of jobs
                    resp = await http_client.get(f"{instance}/api/v1/jobs")
                    if resp.status_code == 200:
                        jobs = resp.json()
                        
                        for job in jobs:
                            status = job.get("Status") or job.get("status", "")
                            job_id_str = job.get("ID") or job.get("id", "")
                            
                            # Only count WORKING jobs (not completed "ok" jobs from previous runs)
                            if status == "working":
                                active_jobs.append(job)
                                
                                # Download CSV to count results
                                try:
                                    csv_resp = await http_client.get(
                                        f"{instance}/api/v1/jobs/{job_id_str}/download",
                                        timeout=5
                                    )
                                    if csv_resp.status_code == 200:
                                        csv_text = csv_resp.text
                                        if csv_text and csv_text.strip():
                                            # Count rows (excluding header)
                                            reader = csv.reader(io.StringIO(csv_text))
                                            row_count = sum(1 for _ in reader) - 1  # Subtract header
                                            if row_count > 0:
                                                total_scraped += row_count
                                                logger.debug(
                                                    "progress_tracker.job_counted",
                                                    instance=instance,
                                                    job_id=job_id_str[:8],
                                                    status=status,
                                                    count=row_count
                                                )
                                except Exception as csv_err:
                                    # CSV download might fail if job just started
                                    logger.debug(
                                        "progress_tracker.csv_download_failed",
                                        instance=instance,
                                        job_id=job_id_str[:8],
                                        error=str(csv_err)[:100]
                                    )
                except Exception as e:
                    logger.debug("progress_tracker.instance_query_failed", instance=instance, error=str(e))
            
            if total_scraped > 0:
                # Calculate progress: 5% (start) + (scraped/max_results * 30%)
                # Scale to 5-35% range (scraping phase)
                progress_pct = min(5 + int((total_scraped / max_results) * 30), 35)
                
                # Calculate ETA
                elapsed = time.time() - start_time
                eta = format_eta(elapsed, progress_pct, 100)
                
                # Create a FRESH database session for thread-safe updates
                fresh_db = SessionLocal()
                try:
                    # Update database
                    job = fresh_db.query(ScrapeJob).filter(ScrapeJob.id == job_uuid).first()
                    if job and job.status == "RUNNING":
                        stats = job.statistics or {}
                        stats["progress_percentage"] = progress_pct
                        stats["progress_message"] = f"🌐 Scraping hotels... ({total_scraped} found so far)"
                        stats["records_so_far"] = total_scraped
                        stats["estimated_time_remaining"] = eta
                        stats["raw_scraped"] = total_scraped  # Update raw count
                        job.statistics = stats
                        fresh_db.commit()
                        
                        logger.info(
                            "progress_tracker.updated",
                            job_id=job_id,
                            scraped=total_scraped,
                            progress=progress_pct,
                            active_jobs=len(active_jobs)
                        )
                        return True
                finally:
                    fresh_db.close()
            else:
                # Fallback: If we can't get count from API, check if jobs are actively running
                # If jobs exist and are working, keep the current progress message
                if len(active_jobs) > 0:
                    fresh_db = SessionLocal()
                    try:
                        job = fresh_db.query(ScrapeJob).filter(ScrapeJob.id == job_uuid).first()
                        if job and job.status == "RUNNING":
                            stats = job.statistics or {}
                            current_progress = stats.get("progress_percentage", 5)
                            
                            # Don't update if we're already past scraping phase (>35%)
                            if current_progress < 35:
                                # Keep current message, just update that we're still working
                                logger.debug(
                                    "progress_tracker.no_count_but_jobs_active",
                                    job_id=job_id,
                                    active_jobs=len(active_jobs),
                                    current_progress=current_progress
                                )
                    finally:
                        fresh_db.close()
            
    except Exception as e:
        logger.warning("progress_tracker.failed", job_id=job_id, error=str(e))
    
    return False


def real_scrape_task_impl(job_id: str):
    """
    Real scraper task implementation for Phase 2.
    
    Uses ScraperOrchestrator to run scrapers with domain grouping and concurrency control,
    then runs CleaningPipeline to process results through 7-step cleaning process.
    Phase 4B: Added geocoding step after cleaning to add coordinates to results.
    Phase 6A: Added MergingPipeline step between cleaning and geocoding (Clean → Merge → Geocode).
    
    Updates job status: QUEUED → RUNNING → DONE/FAILED
    Saves failed_source_ids to database for retry logic.
    
    Includes timeout handling to prevent worker crashes.
    
    Args:
        job_id: UUID string of the scrape job
    """
    from celery.exceptions import SoftTimeLimitExceeded
    
    # Convert job_id string to UUID object
    job_uuid = uuid.UUID(job_id)
    
    db = SessionLocal()
    
    try:
        # Load job from database
        job = db.query(ScrapeJob).filter(ScrapeJob.id == job_uuid).first()
        
        if not job:
            logger.error("job.not_found", job_id=job_id)
            return
        
        # Set status to RUNNING with initial progress
        job.status = "RUNNING"
        job.started_at = datetime.utcnow()
        start_time = time.time()
        
        # Initialize progress tracking
        stats = {
            "raw_scraped": 0,
            "by_source": {},
            "by_source_name": {},
            "new_records": 0,
            "duplicates": 0,
            "updated_records": 0,
            "progress_percentage": 0,
            "progress_message": "🔍 Starting scrape job..."
        }
        job.statistics = stats
        db.commit()
        logger.info("job.started", job_id=job_id, location=job.location, category_id=job.category_id)
        
        # Run orchestrator (async) with timeout handling and real-time progress tracking
        try:
            # Update progress: Scraping phase started
            # Get category name for progress message
            from models import Category
            category = db.query(Category).filter(Category.id == job.category_id).first()
            category_name = category.name if category else "results"
            
            stats["progress_percentage"] = 5
            stats["progress_message"] = f"🌐 Scraping {category_name} in {job.location}..."
            job.statistics = stats
            db.commit()
            
            # Create a background task for orchestrator
            orchestrator = ScraperOrchestrator()
            
            # Run orchestrator with periodic progress updates based on phase
            async def run_with_progress_tracking():
                """Run orchestrator while showing phase-based progress."""
                logger.info("progress_tracker.starting", job_id=job_id)
                
                # Start orchestrator as a task
                orchestrator_task = asyncio.create_task(
                    orchestrator.run_async(db, str(job_uuid))
                )
                
                logger.info("progress_tracker.orchestrator_task_created", job_id=job_id, task_done=orchestrator_task.done())
                
                # Progress tracking variables
                progress_poll_interval = 3  # seconds
                poll_count = 0
                
                # Phase-based progress messages
                phase_messages = [
                    (0, 10, "🔍 Searching Google Maps..."),
                    (10, 20, "🔍 Exploring search area..."),
                    (20, 30, "📍 Finding locations..."),
                    (30, 35, "🔍 Completing search..."),
                ]
                
                while not orchestrator_task.done():
                    await asyncio.sleep(progress_poll_interval)
                    poll_count += 1
                    
                    logger.debug("progress_tracker.poll_iteration", job_id=job_id, poll_count=poll_count, task_done=orchestrator_task.done())
                    
                    try:
                        # Determine phase based on elapsed time
                        # Typical scraping takes 2-5 minutes, spread progress across that
                        elapsed = time.time() - start_time
                        elapsed_minutes = elapsed / 60
                        
                        # Progress grows smoothly: 5% + (time-based growth to 35%)
                        # Assume scraping takes ~4 minutes on average
                        progress_pct = min(5 + int((elapsed_minutes / 4) * 30), 35)
                        
                        # Select message based on progress
                        message = phase_messages[0][2]  # default
                        for start, end, msg in phase_messages:
                            if start <= progress_pct < end:
                                message = msg
                                break
                        
                        # Update database
                        progress_db = SessionLocal()
                        try:
                            progress_job = progress_db.query(ScrapeJob).filter(ScrapeJob.id == job_uuid).first()
                            if progress_job and progress_job.status == "RUNNING":
                                # Get category name
                                from models import Category
                                category = progress_db.query(Category).filter(Category.id == progress_job.category_id).first()
                                category_name = category.name if category else "results"
                                
                                stats = progress_job.statistics or {}
                                stats["progress_percentage"] = progress_pct
                                stats["progress_message"] = f"{message} ({category_name} in {progress_job.location})"
                                progress_job.statistics = stats
                                
                                # Force JSONB update by marking as modified
                                from sqlalchemy.orm.attributes import flag_modified
                                flag_modified(progress_job, "statistics")
                                
                                progress_db.commit()
                                progress_db.refresh(progress_job)
                                
                                logger.info(
                                    "progress_update.phase_based",
                                    job_id=job_id,
                                    progress=progress_pct,
                                    message=message,
                                    elapsed_minutes=round(elapsed_minutes, 2),
                                    db_committed=True
                                )
                            else:
                                logger.warning("progress_update.job_not_found_or_not_running", job_id=job_id)
                        except Exception as db_err:
                            logger.error("progress_update.db_error", job_id=job_id, error=str(db_err), exc_info=True)
                        finally:
                            progress_db.close()
                                
                    except Exception as progress_err:
                        logger.warning("progress_update_error", job_id=job_id, error=str(progress_err))
                
                logger.info("progress_tracker.loop_ended", job_id=job_id, poll_count=poll_count)
                
                # Get orchestrator result
                return await orchestrator_task
            
            # Run orchestrator with progress tracking
            raw_results, failed_source_ids = asyncio.run(run_with_progress_tracking())
        except SoftTimeLimitExceeded:
            logger.error("job.timeout", job_id=job_id, message="Task exceeded soft time limit")
            job.status = "FAILED"
            job.error_message = "Task timeout: exceeded 85 minute limit"
            job.completed_at = datetime.utcnow()
            db.commit()
            return
        except Exception as e:
            logger.error("job.orchestrator_failed", job_id=job_id, error=str(e), exc_info=True)
            job.status = "FAILED"
            job.error_message = f"Orchestrator error: {str(e)}"
            job.completed_at = datetime.utcnow()
            db.commit()
            return
        
        logger.info(
            "job.orchestrator_complete",
            job_id=job_id,
            raw_result_count=len(raw_results),
            failed_sources=len(failed_source_ids)
        )
        
        # Update progress: Scraping complete
        elapsed = time.time() - start_time
        stats["raw_scraped"] = len(raw_results)
        stats["progress_percentage"] = 35
        stats["progress_message"] = f"✅ Search complete - found {len(raw_results)} results"
        job.statistics = stats
        db.commit()
        
        # Load source names for display
        from models.source import Source
        source_map = {}
        for result in raw_results:
            source_id = result.get("source_id", 1)
            if source_id not in source_map:
                source = db.query(Source).filter(Source.id == source_id).first()
                if source:
                    source_map[source_id] = source.display_name or source.name
        
        # Count results by source
        for result in raw_results:
            source_id = result.get("source_id", 1)
            stats["by_source"][source_id] = stats["by_source"].get(source_id, 0) + 1
            
            # Also track by source name for display
            source_name = source_map.get(source_id, f"Source #{source_id}")
            stats["by_source_name"][source_name] = stats["by_source_name"].get(source_name, 0) + 1
        
        # Run cleaning pipeline for each source's results
        # Update progress: Starting cleaning
        stats["progress_percentage"] = 40
        stats["progress_message"] = "🧹 Cleaning and validating data..."
        job.statistics = stats
        db.commit()
        
        total_cleaned = 0
        total_updated = 0
        
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
            cleaned_results, updated_count = cleaner.process(
                source_results,
                str(job_uuid),
                source_id,
                job.category_id
            )
            total_cleaned += len(cleaned_results)
            total_updated += updated_count
            
            # Count new vs duplicate records based on flags (not difference)
            # Now that we save duplicates for visibility, we need to count by flags
            new_count = sum(1 for r in cleaned_results if r.get("is_new_record", True))
            duplicate_count = sum(1 for r in cleaned_results if not r.get("is_new_record", True) and not r.get("is_updated_record", False))
            stats["duplicates"] += duplicate_count
            stats["new_records"] += new_count
        
        # Updated records already tracked
        stats["updated_records"] = total_updated
        
        logger.info(
            "job.cleaning_complete",
            job_id=job_id,
            cleaned_result_count=total_cleaned,
            updated_record_count=total_updated
        )
        
        # Update progress message after cleaning
        stats["progress_percentage"] = 60
        stats["progress_message"] = f"✅ Validation complete - {stats['new_records']} new, {stats['duplicates']} duplicates, {stats['updated_records']} updated"
        job.statistics = stats
        db.commit()
        
        # Phase 6A: Merge results from multiple sources (Clean → Merge → Geocode)
        if total_cleaned > 0:
            try:
                # Update progress before merging
                stats["progress_percentage"] = 70
                stats["progress_message"] = "🔄 Merging data from multiple sources..."
                job.statistics = stats
                db.commit()
                
                from scrapers.merger import MergingPipeline
                merge_stats = MergingPipeline(db).run(str(job_uuid))
                logger.info(
                    "job.merging_complete",
                    job_id=job_id,
                    merged_groups=merge_stats["merged_groups"],
                    total_records_processed=merge_stats["total_records_processed"]
                )
                
                # Update progress after merging
                stats["progress_percentage"] = 80
                stats["progress_message"] = f"✅ Merging complete - {merge_stats['merged_groups']} groups merged"
                job.statistics = stats
                db.commit()
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
                # Update progress before geocoding
                stats["progress_percentage"] = 85
                stats["progress_message"] = "📍 Adding location coordinates..."
                job.statistics = stats
                db.commit()
                
                geocoded_count = asyncio.run(
                    geocode_job_results(db, str(job_uuid))
                )
                logger.info(
                    "job.geocoding_complete",
                    job_id=job_id,
                    geocoded_count=geocoded_count
                )
                
                # Update progress after geocoding
                stats["progress_percentage"] = 95
                stats["progress_message"] = f"✅ Geocoding complete - {geocoded_count} locations added"
                job.statistics = stats
                db.commit()
            except Exception as geocoding_error:
                # Log error but don't fail the job
                logger.warning(
                    "job.geocoding_failed",
                    job_id=job_id,
                    error=str(geocoding_error),
                    exc_info=True
                )
        
        # Update job with results and statistics
        stats["progress_percentage"] = 100
        stats["progress_message"] = "✨ Job complete!"
        job.status = "DONE"
        job.completed_at = datetime.utcnow()
        job.failed_source_ids = failed_source_ids if failed_source_ids else None
        job.statistics = stats  # Save statistics for display
        db.commit()
        
        logger.info(
            "job.done",
            job_id=job_id,
            result_count=total_cleaned,
            failed_sources=len(failed_source_ids),
            raw_scraped=stats["raw_scraped"],
            new_records=stats["new_records"],
            duplicates=stats["duplicates"],
            updated_records=stats["updated_records"]
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
