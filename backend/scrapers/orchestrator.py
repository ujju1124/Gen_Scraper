"""
Scraper Orchestrator for Web Scraping Portal Phase 2

This module orchestrates the execution of multiple scrapers with:
- Domain grouping for rate limiting
- Sequential execution within same domain (2s delay)
- Parallel execution across different domains
- Failure tracking and partial success handling
"""

import asyncio
import uuid
from urllib.parse import urlparse
from typing import Tuple, Optional
from datetime import datetime

import structlog
from sqlalchemy.orm import Session

from models.scrape_job import ScrapeJob
from models.source import Source
from scrapers.registry import get_scraper

logger = structlog.get_logger()


class ScraperOrchestrator:
    """
    Orchestrates scraper execution with domain-based concurrency control.
    
    Features:
    - Groups sources by domain
    - Runs same-domain scrapers sequentially (prevents rate limiting)
    - Runs different-domain scrapers in parallel (maximizes throughput)
    - Tracks failures and returns partial results
    """
    
    def __init__(self):
        """Initialize the orchestrator."""
        self.delay_between_requests = 2.0  # seconds
    
    async def run_async(self, db: Session, job_id: str) -> Tuple[list[dict], list[int]]:
        """
        Main entry point for orchestrator.
        
        Loads job from database, groups sources by domain, executes scrapers
        with concurrency control, and returns results with failure tracking.
        
        Args:
            db: SQLAlchemy database session
            job_id: UUID of the scrape job (string or UUID object)
            
        Returns:
            Tuple of (results, failed_source_ids)
            - results: List of scraped data dictionaries
            - failed_source_ids: List of source IDs that failed
            
        Example:
            >>> orchestrator = ScraperOrchestrator()
            >>> results, failed_ids = await orchestrator.run_async(db, job_id)
        """
        results = []
        failed_source_ids = []
        
        try:
            # Convert job_id to UUID if it's a string
            job_uuid = uuid.UUID(job_id) if isinstance(job_id, str) else job_id
            
            # Load job from database
            job = db.query(ScrapeJob).filter(ScrapeJob.id == job_uuid).first()
            
            if not job:
                logger.error("orchestrator.job_not_found", job_id=job_id)
                return [], []
            
            logger.info(
                "orchestrator.started",
                job_id=job_id,
                location=job.location,
                category_id=job.category_id,
                max_results=job.max_results
            )
            
            # Load sources
            sources = self._load_sources(db, job)
            
            if not sources:
                logger.warning(
                    "orchestrator.no_sources",
                    job_id=job_id,
                    category_id=job.category_id
                )
                return [], []
            
            logger.info(
                "orchestrator.sources_loaded",
                job_id=job_id,
                source_count=len(sources)
            )
            
            # Group sources by domain
            domain_groups = self._group_by_domain(sources)
            
            logger.info(
                "orchestrator.domain_groups_created",
                job_id=job_id,
                domain_count=len(domain_groups)
            )
            
            # Run domain groups in parallel
            domain_results = await asyncio.gather(
                *[
                    self._run_domain_group(db, job, domain, sources_in_domain, job.max_results)
                    for domain, sources_in_domain in domain_groups.items()
                ],
                return_exceptions=True
            )
            
            # Collect results and failures
            for domain_result in domain_results:
                if isinstance(domain_result, Exception):
                    logger.error(
                        "orchestrator.domain_group_failed",
                        job_id=job_id,
                        error=str(domain_result)
                    )
                    continue
                
                domain_data, domain_failures = domain_result
                results.extend(domain_data)
                failed_source_ids.extend(domain_failures)
            
            logger.info(
                "orchestrator.completed",
                job_id=job_id,
                total_results=len(results),
                failed_sources=len(failed_source_ids)
            )
            
        except Exception as e:
            logger.error(
                "orchestrator.failed",
                job_id=job_id,
                error=str(e),
                exc_info=True
            )
            raise
        
        return results, failed_source_ids
    
    def _load_sources(self, db: Session, job: ScrapeJob) -> list[Source]:
        """
        Load sources for the job.
        
        If job.source_ids is specified, load only those sources.
        If job.source_ids is empty/None, load NO category-specific sources.
        
        Always appends Google Maps as universal source when active.
        
        Args:
            db: SQLAlchemy database session
            job: ScrapeJob instance
            
        Returns:
            List of Source instances
        """
        sources = []
        
        # Only load category-specific sources if source_ids is explicitly provided
        if job.source_ids:
            sources = db.query(Source).filter(
                Source.is_active == True,
                Source.category_id == job.category_id,
                Source.id.in_(job.source_ids)
            ).all()
            
            logger.debug(
                "orchestrator.sources_query",
                job_id=job.id,
                category_id=job.category_id,
                source_ids=job.source_ids,
                found_count=len(sources)
            )
        else:
            logger.info(
                "orchestrator.no_sources_selected",
                job_id=job.id,
                message="No sources selected - will run only Google Maps"
            )
        
        # Always add Google Maps as universal source when active
        google_maps_source = db.query(Source).filter(
            Source.name == "google_maps",
            Source.is_active == True
        ).first()
        
        if google_maps_source and google_maps_source.id not in [s.id for s in sources]:
            sources.append(google_maps_source)
            logger.info(
                "orchestrator.google_maps_appended",
                job_id=job.id,
                google_maps_source_id=google_maps_source.id
            )
        
        return sources
    
    def _group_by_domain(self, sources: list[Source]) -> dict[str, list[Source]]:
        """
        Group sources by base domain.
        
        Extracts domain from source.base_url using urlparse.
        Sources with same domain are grouped together for sequential execution.
        
        Args:
            sources: List of Source instances
            
        Returns:
            Dictionary mapping domain to list of sources
            
        Example:
            >>> sources = [booking_com, agoda, tripadvisor]
            >>> groups = self._group_by_domain(sources)
            >>> # {"booking.com": [booking_com], "agoda.com": [agoda], ...}
        """
        domain_groups = {}
        
        for source in sources:
            try:
                # Extract domain from base_url
                parsed = urlparse(source.base_url)
                domain = parsed.netloc or parsed.path
                
                # Remove www. prefix if present
                if domain.startswith('www.'):
                    domain = domain[4:]
                
                if domain not in domain_groups:
                    domain_groups[domain] = []
                
                domain_groups[domain].append(source)
                
                logger.debug(
                    "orchestrator.source_grouped",
                    source_id=source.id,
                    source_name=source.name,
                    domain=domain
                )
                
            except Exception as e:
                logger.warning(
                    "orchestrator.domain_extraction_failed",
                    source_id=source.id,
                    base_url=source.base_url,
                    error=str(e)
                )
                # Fallback: use source name as domain
                domain = source.name
                if domain not in domain_groups:
                    domain_groups[domain] = []
                domain_groups[domain].append(source)
        
        return domain_groups
    
    async def _run_domain_group(
        self,
        db: Session,
        job: ScrapeJob,
        domain: str,
        sources: list[Source],
        max_results: Optional[int] = None
    ) -> Tuple[list[dict], list[int]]:
        """
        Run scrapers for same domain sequentially with delay.
        
        Executes scrapers one at a time with 2-second delay between requests
        to prevent rate limiting from the same domain.
        
        Args:
            db: SQLAlchemy database session
            job: ScrapeJob instance
            domain: Domain name
            sources: List of sources for this domain
            max_results: Maximum results to collect per source (None = unlimited)
            
        Returns:
            Tuple of (results, failed_source_ids)
        """
        results = []
        failed_source_ids = []
        
        logger.info(
            "orchestrator.domain_group_started",
            job_id=job.id,
            domain=domain,
            source_count=len(sources),
            max_results=max_results
        )
        
        for idx, source in enumerate(sources):
            try:
                # Get scraper instance from registry
                scraper = get_scraper(source.name)
                
                logger.info(
                    "orchestrator.scraper_starting",
                    job_id=job.id,
                    source_id=source.id,
                    source_name=source.name,
                    domain=domain,
                    max_results=max_results
                )
                
                # Run scraper (pass location and max_results from job) with timeout
                try:
                    # Adjust timeout based on scraper type
                    # Directory of Nepal needs more time due to detail page fetching per listing
                    # Google Maps Go scraper needs time for deep crawling
                    if "directoryofnepal" in source.name:
                        timeout_seconds = 1800.0  # 30 minutes for Directory of Nepal
                    elif source.name == "google_maps":
                        timeout_seconds = 3600.0  # 60 minutes for Google Maps
                        # Kathmandu: 12 neighbourhoods → 3 batches × ~8 min = ~24 min
                        # Pokhara:    9 neighbourhoods → 3 batches × ~8 min = ~24 min
                        # Plus browser startup (~2 min) + dedup + buffer = ~30 min total
                        # 60 min gives comfortable headroom for any city
                    else:
                        timeout_seconds = 900.0   # 15 minutes for all other scrapers (Booking.com etc.)
                    
                    source_results = await asyncio.wait_for(
                        scraper.run(source, db, job.location, max_results=max_results, category_id=job.category_id),
                        timeout=timeout_seconds
                    )
                except asyncio.TimeoutError:
                    logger.error(
                        "orchestrator.scraper_timeout",
                        job_id=job.id,
                        source_id=source.id,
                        source_name=source.name,
                        timeout_seconds=timeout_seconds
                    )
                    failed_source_ids.append(source.id)
                    continue
                
                if source_results:
                    # Add source_id to each result
                    for result in source_results:
                        result["source_id"] = source.id
                    
                    results.extend(source_results)
                    logger.info(
                        "orchestrator.scraper_succeeded",
                        job_id=job.id,
                        source_id=source.id,
                        source_name=source.name,
                        result_count=len(source_results)
                    )
                else:
                    logger.warning(
                        "orchestrator.scraper_no_results",
                        job_id=job.id,
                        source_id=source.id,
                        source_name=source.name
                    )
                
                # Delay between same-domain requests (except after last source)
                if idx < len(sources) - 1:
                    logger.debug(
                        "orchestrator.delaying",
                        domain=domain,
                        delay_seconds=self.delay_between_requests
                    )
                    await asyncio.sleep(self.delay_between_requests)
                
            except ValueError as e:
                # Scraper not found in registry
                logger.error(
                    "orchestrator.scraper_not_found",
                    job_id=job.id,
                    source_id=source.id,
                    source_name=source.name,
                    error=str(e)
                )
                failed_source_ids.append(source.id)
                
            except Exception as e:
                # Scraper execution failed
                logger.error(
                    "orchestrator.scraper_failed",
                    job_id=job.id,
                    source_id=source.id,
                    source_name=source.name,
                    error=str(e),
                    exc_info=True
                )
                failed_source_ids.append(source.id)
        
        logger.info(
            "orchestrator.domain_group_completed",
            job_id=job.id,
            domain=domain,
            results=len(results),
            failures=len(failed_source_ids)
        )
        
        return results, failed_source_ids
