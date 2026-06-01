"""
Go Scraper API Client  (web-mode)

Calls the Go-based Google Maps scraper running in -web mode (SQLite, no auth).

API endpoints (web mode):
  POST /api/v1/jobs          → submit a job, returns {"id": "<uuid>"}
  GET  /api/v1/jobs/{id}     → poll status/results
  DELETE /api/v1/jobs/{id}   → delete a job

Job statuses: "pending" | "working" | "ok" | "failed"

The Go scraper returns CSV rows per result. This client:
  1. Submits the job with keyword + location settings
  2. Polls until status == "ok" or "failed"
  3. Downloads the CSV and parses it into dicts
  4. Maps CSV columns to the Python backend's standard result format
"""

import asyncio
import csv
import io
import time
from typing import Optional

import httpx
import structlog

from config import settings
from scrapers.go_scraper_pool import go_scraper_pool

logger = structlog.get_logger()

# Neighborhood keywords for major Nepal cities
# Use simple format: "Thamel" not "Thamel Kathmandu" or "restaurants in Thamel"
# The category will be prepended: "restaurants in Thamel, Kathmandu"
NEIGHBORHOOD_KEYWORDS = {
    "kathmandu": [
        "Thamel",
        "Durbar Marg",
        "New Road",
        "Patan",
        "Baneshwor",
        "Lazimpat",
        "Boudha",
        "Swayambhu",
        # Chabahil, Maharajgunj, Koteshwor, Kalanki removed to keep within 2 batches
        # 8 neighbourhoods × ~5 min = ~10 min total (well within 60 min limit)
        # Add them back if you need more coverage
    ],
    "pokhara": [
        "Lakeside",
        "Baidam",
        "Damside",
        "Prithvi Chowk",
        "Mahendrapul",
        "Sabhagriha",
        "Newroad",
        "Chipledhunga",
        "Baglung Bus Park",
    ],
    "biratnagar": [
        "Traffic Chowk",
        "Ghantaghar",
        "Rangeli Road",
        "Buddhashanti",
        "Main Road",
        "Tinpaini",
    ],
    "dharan": [
        "Bhanuchowk",
        "Chatara Road",
        "Dharan Bazaar",
        "BP Chowk",
        "Pindeshwor",
    ],
    "birgunj": [
        "Ghantaghar",
        "Adarshanagar",
        "Clock Tower",
        "Main Road",
        "Parsauni",
    ],
    "bharatpur": [
        "Pulchowk",
        "Narayangadh",
        "Sahid Chowk",
        "Ratnanagar",
    ],
    "chitwan": [
        "Narayangadh",
        "Bharatpur",
        "Ratnanagar",
        "Sauraha",
    ],
    "lalitpur": [
        "Jawalakhel",
        "Pulchowk",
        "Kupondole",
        "Sanepa",
    ],
    "bhaktapur": [
        "Durbar Square",
        "Suryabinayak",
        "Thimi",
    ],
}


class GoScraperClient:
    """
    HTTP client for the Go Google Maps scraper (web mode, no auth).

    Usage:
        client = GoScraperClient()
        results = await client.scrape(
            keyword="hotels in Kathmandu",
            geo_coordinates="27.693444,85.281924",
            zoom=14,
            max_depth=5,
        )
    """

    def __init__(self):
        # Don't set base_url here - we'll get it from the pool
        self.timeout = settings.GO_SCRAPER_TIMEOUT
        self.poll_interval = settings.GO_SCRAPER_POLL_INTERVAL
        # Web mode has no authentication
        self._headers = {"Content-Type": "application/json"}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def scrape(
        self,
        keyword: str,
        geo_coordinates: str = "",
        zoom: int = 14,
        max_depth: int = 5,
        radius: float = 0,
        lang: str = "en",
        extract_emails: bool = False,
        extra_reviews: bool = False,
        fast_mode: bool = False,
    ) -> list[dict]:
        """
        Submit a scrape job to the Go service and wait for results.

        Returns list of result dicts in the Python backend's standard format.
        """
        if not settings.GO_SCRAPER_ENABLED:
            logger.info("go_scraper.disabled")
            return []

        # Get available instance from pool (least busy strategy)
        base_url = await go_scraper_pool.get_least_busy_instance()
        
        if not base_url:
            logger.warning(
                "go_scraper.no_instances_available",
                message="All Go scraper instances are busy or down, falling back to Playwright"
            )
            return []
        
        logger.info(
            "go_scraper.using_instance",
            instance=base_url,
            keyword=keyword
        )

        # Parse lat/lon from geo_coordinates string
        lat, lon = "", ""
        if geo_coordinates:
            parts = geo_coordinates.split(",")
            if len(parts) == 2:
                lat = parts[0].strip()
                lon = parts[1].strip()

        # Web mode requires max_time in seconds (as integer, converted to Duration)
        # Minimum is 180 seconds per the Go validation
        # Calculate timeout dynamically based on settings and max_depth
        
        # Estimate results based on max_depth (rough approximation)
        estimated_results = min(max_depth * 3, 100)  # ~3 results per depth level, cap at 100
        
        if extract_emails:
            # Email extraction: 15 seconds per result + 180s base
            max_time_seconds = 180 + (estimated_results * 15)
            max_time_seconds = max(300, min(max_time_seconds, 1200))
        else:
            # No email extraction: 5 seconds per result + 180s base
            # 180s covers Go scraper startup + browser download + first scroll
            max_time_seconds = 180 + (estimated_results * 5)
            # Cap between 300s (5 min minimum) and 900s (15 min maximum)
            max_time_seconds = max(300, min(max_time_seconds, 900))
        
        logger.info(
            "go_scraper.timeout_calculated",
            keyword=keyword,
            max_depth=max_depth,
            estimated_results=estimated_results,
            extract_emails=extract_emails,
            max_time_seconds=max_time_seconds,
        )

        # Build request payload for web mode API
        payload: dict = {
            "name": f"scrape-{keyword[:40]}",
            "keywords": [keyword],
            "lang": lang,
            "zoom": zoom,
            "depth": max(1, max_depth),
            "fast_mode": fast_mode,
            "email": extract_emails,
            "radius": int(radius * 1000) if radius > 0 else 10000,  # km → meters
            "max_time": min(int(max_time_seconds), 3600),  # Go scraper expects "max_time", not "timeout" (Stay under Go's 3600s limit)
            "lat": lat,
            "lon": lon,
        }
        
        logger.info(
            "go_scraper.payload_debug",
            keyword=keyword,
            payload=payload,
            max_time_seconds=max_time_seconds,
        )

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                # Step 1: Submit job to selected instance
                job_id = await self._submit_job(client, payload, base_url)
                if not job_id:
                    return []

                logger.info(
                    "go_scraper.job_submitted",
                    job_id=job_id,
                    keyword=keyword,
                    instance=base_url
                )

                # Step 2: Poll until done (pass max_time_seconds for dynamic timeout)
                job_data = await self._poll_until_done(client, job_id, keyword, max_time_seconds, base_url)

            # Step 3: Download CSV and parse
            # Handle both "Status" (Go API) and "status" (lowercase)
            status = job_data.get("Status") or job_data.get("status", "") if job_data else ""
            
            # Try to download results if job completed OR if we have partial results from timeout
            if job_data and (status == "ok" or status == "working"):
                results = await self._download_and_parse(job_id, keyword, base_url)
                
                if results:
                    if status == "ok":
                        logger.info(
                            "go_scraper.download_complete",
                            keyword=keyword,
                            result_count=len(results),
                            status="completed",
                            instance=base_url
                        )
                    else:
                        logger.warning(
                            "go_scraper.partial_results_downloaded",
                            keyword=keyword,
                            result_count=len(results),
                            status=status,
                            message="Downloaded partial results before timeout - Playwright will complete the rest",
                            instance=base_url
                        )
                    return results
                else:
                    logger.warning(
                        "go_scraper.no_results_available",
                        job_id=job_id,
                        status=status,
                        message="No results available to download",
                        instance=base_url
                    )
            else:
                logger.warning(
                    "go_scraper.job_not_ok",
                    job_id=job_id,
                    job_data=job_data,
                    status=status,
                    instance=base_url
                )

        except httpx.ConnectError:
            logger.warning(
                "go_scraper.connection_failed",
                instance=base_url,
                message="Go scraper not reachable — falling back to Playwright",
            )
        except httpx.TimeoutException:
            logger.warning(
                "go_scraper.timeout",
                keyword=keyword,
                timeout=self.timeout,
            )
        except Exception as e:
            logger.error(
                "go_scraper.unexpected_error",
                keyword=keyword,
                error=str(e),
                exc_info=True,
            )

        return []

    async def health_check(self) -> bool:
        """Return True if at least one Go scraper instance is reachable."""
        health_status = await go_scraper_pool.health_check_all()
        return any(health_status.values())

    async def _scrape_neighborhoods(
        self,
        keyword: str,
        location: str,
        total_results: int,
        zoom: int = 15,
        lang: str = "en",
        extract_emails: bool = False,
    ) -> list[dict]:
        """
        Scrape using neighborhood keywords in batches.
        
        Batch size = number of Go scraper instances (4).
        Each batch runs in parallel, batches run sequentially.
        This prevents queue congestion while maximizing speed.
        
        Example for Kathmandu (12 neighborhoods):
        - Batch 1: Thamel, Durbar Marg, New Road, Patan → all 4 run in parallel (~4 min)
        - Batch 2: Baneshwor, Lazimpat, Boudha, Swayambhu → all 4 run in parallel (~4 min)
        - Batch 3: Chabahil, Maharajgunj, Koteshwor, Kalanki → all 4 run in parallel (~4 min)
        Total: ~12 minutes ✅ (well under 30 min orchestrator limit)
        """
        import asyncio
        import math

        # Get neighborhoods for this city (using module-level NEIGHBORHOOD_KEYWORDS)
        neighborhoods = NEIGHBORHOOD_KEYWORDS.get(location.lower(), [])
        
        if not neighborhoods:
            logger.warning(
                "go_scraper.no_neighborhoods_defined",
                location=location,
                message="No neighborhoods defined for this city — falling back to quadrant chunking"
            )
            return []

        # Extract category from keyword
        category = keyword.split(" in ")[0] if " in " in keyword else keyword

        instances = [
            "http://go_scraper_1:8080",
            "http://go_scraper_2:8080",
            "http://go_scraper_3:8080",
            "http://go_scraper_4:8080",
        ]
        
        BATCH_SIZE = len(instances)  # 4

        logger.info(
            "go_scraper.neighborhood_search_start",
            location=location,
            category=category,
            total_neighborhoods=len(neighborhoods),
            batch_size=BATCH_SIZE,
            total_batches=math.ceil(len(neighborhoods) / BATCH_SIZE),
            total_requested=total_results,
        )

        all_results = []
        
        # Clear ALL queues ONCE at the start (before any batches)
        # This removes stuck jobs from previous runs
        logger.info("go_scraper.clearing_all_queues_once", total_instances=len(instances))
        clear_tasks = [
            self._clear_instance_queue(inst)
            for inst in instances
        ]
        await asyncio.gather(*clear_tasks, return_exceptions=True)
        await asyncio.sleep(3)  # Wait for queues to stabilize
        
        # Process neighborhoods in batches of 4
        for batch_start in range(0, len(neighborhoods), BATCH_SIZE):
            batch = neighborhoods[batch_start:batch_start + BATCH_SIZE]
            batch_num = (batch_start // BATCH_SIZE) + 1
            total_batches = math.ceil(len(neighborhoods) / BATCH_SIZE)
            
            logger.info(
                "go_scraper.batch_start",
                batch_num=batch_num,
                total_batches=total_batches,
                neighborhoods=batch
            )
            
            # Submit this batch in parallel (one neighborhood per instance)
            tasks = []
            for i, neighborhood in enumerate(batch):
                instance = instances[i % len(instances)]
                # Use format: "restaurants in Thamel, Kathmandu" (with city for disambiguation)
                # This prevents ambiguous neighborhoods like "Durbar Square" from returning results from multiple cities
                neighborhood_keyword = f"{category} in {neighborhood}, {location}"

                logger.info(
                    "go_scraper.neighborhood_assigned",
                    neighborhood=neighborhood,
                    keyword=neighborhood_keyword,
                    instance=instance,
                    batch_num=batch_num,
                )

                task = self._scrape_single_chunk(
                    keyword=neighborhood_keyword,  # Full keyword with neighborhood
                    chunk_index=batch_start + i,
                    depth=8,             # depth=8 → ~60-80 results, ~4 min per neighbourhood
                    instance=instance,
                    geo_coordinates="",  # No coordinates - keyword drives search
                    zoom=zoom,
                    radius=0,            # No radius - keyword drives search
                    lang=lang,
                    extract_emails=extract_emails,
                )
                tasks.append((neighborhood, task))
            
            # Wait for ALL tasks in this batch to complete before starting next batch
            batch_tasks = [t for _, t in tasks]
            batch_neighborhoods = [n for n, _ in tasks]
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # Process batch results
            batch_success = 0
            batch_failed = 0
            
            for i, result in enumerate(batch_results):
                neighborhood = batch_neighborhoods[i]
                
                if isinstance(result, Exception):
                    logger.warning(
                        "go_scraper.neighborhood_failed",
                        neighborhood=neighborhood,
                        error=str(result),
                        batch_num=batch_num
                    )
                    batch_failed += 1
                elif result and len(result) > 0:
                    all_results.extend(result)
                    batch_success += 1
                    logger.info(
                        "go_scraper.neighborhood_complete",
                        neighborhood=neighborhood,
                        result_count=len(result),
                        batch_num=batch_num
                    )
                else:
                    logger.warning(
                        "go_scraper.neighborhood_empty",
                        neighborhood=neighborhood,
                        batch_num=batch_num
                    )
                    batch_failed += 1
            
            logger.info(
                "go_scraper.batch_complete",
                batch_num=batch_num,
                total_batches=total_batches,
                batch_success=batch_success,
                batch_failed=batch_failed,
                total_so_far=len(all_results)
            )
            
            # Early exit: if we have enough results, no need to run remaining batches
            if len(all_results) >= total_results * 1.5:
                logger.info(
                    "go_scraper.early_exit",
                    collected=len(all_results),
                    threshold=total_results * 1.5,
                    message="Enough results collected, skipping remaining batches"
                )
                break
        
        # Deduplicate — use place_id first (reliable)
        # then fall back to name+address
        seen_place_ids = set()
        seen_name_addr = set()
        unique_results = []
        
        for r in all_results:
            # Try place_id first (most reliable)
            place_id = r.get("extra_data", {}).get("place_id", "").strip()
            if not place_id:
                # Fallback: check top-level place_id (if exists)
                place_id = r.get("place_id", "").strip()
            
            if place_id:
                if place_id not in seen_place_ids:
                    seen_place_ids.add(place_id)
                    unique_results.append(r)
            else:
                # No place_id, use name+address
                key = (
                    r.get("name", "").lower().strip(),
                    r.get("address", "").lower().strip()
                )
                if key not in seen_name_addr and key != ("", ""):
                    seen_name_addr.add(key)
                    unique_results.append(r)
        
        duplicate_rate = round(
            (1 - len(unique_results) / max(len(all_results), 1)) * 100, 1
        )
        
        logger.info(
            "go_scraper.neighborhood_search_complete",
            location=location,
            category=category,
            total_collected=len(all_results),
            after_dedup=len(unique_results),
            duplicate_rate=f"{duplicate_rate}%"
        )
        
        return unique_results[:total_results]

    async def scrape_large(
        self,
        keyword: str,
        total_results: int,
        location: str = "",
        geo_coordinates: str = "",
        zoom: int = 14,
        radius: float = 5,
        lang: str = "en",
        extract_emails: bool = False,
    ) -> list[dict]:
        """
        For large jobs (>150 results): uses neighborhood search or quadrant chunking.
        
        STRATEGY 1: Neighborhood keyword search (primary, for known cities)
        - Uses neighborhood names in keywords: "restaurants Thamel"
        - Each neighborhood = different search = different results
        - Expected: 400-600 unique results, 20-40% duplicate rate
        - Supported: 56 cities across Nepal (Kathmandu, Pokhara, Biratnagar, Dharan,
          Birgunj, Bharatpur, Chitwan, Lalitpur, Bhaktapur, Hetauda, Butwal, Nepalgunj,
          Janakpur, Itahari, Dhangadhi, Tulsipur, Siddharthanagar, Ghorahi, Damak,
          Mechinagar, Birendranagar, Kalaiya, Rajbiraj, Lahan, Gaur, Bardibas, Malangwa,
          Triyuga, Birtamod, Bhadrapur, Tansen, Mahendranagar, Ilam, Jaleshwar, Simara,
          Kohalpur, Urlabari, Inaruwa, Dhankuta, Baglung, Waling, Putalibazar, Tikapur,
          Dipayal, Dadeldhura, Bhojpur, Khandbari, Phidim, Mirchaiya, Rajpur, Chandranigahapur)
        
        STRATEGY 2: Quadrant chunking (fallback for unknown cities)
        - Repeats same search multiple times
        - Expected: ~120 unique results, 75% duplicate rate
        - Used when city has no neighborhood data
        
        Note: Coordinate-based grid search removed (May 30, 2026)
        - Go scraper ignores lat/lon parameters (confirmed by testing)
        - Uses IP-based location instead
        - Coordinate approach will never work
        """
        import asyncio
        
        # STRATEGY 1: Try neighborhood search first (for known cities)
        if location:
            logger.info(
                "go_scraper.trying_neighborhood_search",
                location=location,
                keyword=keyword,
                total_results=total_results
            )
            
            neighborhood_results = await self._scrape_neighborhoods(
                keyword=keyword,
                location=location,
                total_results=total_results,
                zoom=zoom,
                lang=lang,
                extract_emails=extract_emails,
            )
            
            if neighborhood_results:
                logger.info(
                    "go_scraper.neighborhood_search_succeeded",
                    location=location,
                    result_count=len(neighborhood_results)
                )
                return neighborhood_results
            
            # If neighborhood search returned empty, fall through to quadrant chunking
            logger.warning(
                "go_scraper.neighborhood_search_failed",
                location=location,
                reason="No neighborhood data or all neighborhoods returned 0 results"
            )
        
        # STRATEGY 2: Quadrant chunking fallback
        logger.info(
            "go_scraper.using_quadrant_chunking",
            location=location,
            total_results=total_results,
            reason="No location specified or neighborhood search unavailable"
        )

        # Use original chunk size - it performs better
        CHUNK_SIZE = 100
        depth_per_chunk = 15  # ~8 results per depth
        num_chunks = (total_results + CHUNK_SIZE - 1) // CHUNK_SIZE

        logger.info(
            "go_scraper.chunked_start",
            keyword=keyword,
            total_results=total_results,
            num_chunks=num_chunks,
            chunk_size=CHUNK_SIZE
        )

        # Get all available Go instances
        # All containers expose port 8080 internally
        instances = [
            "http://go_scraper_1:8080",
            "http://go_scraper_2:8080",
            "http://go_scraper_3:8080",
            "http://go_scraper_4:8080",
        ]

        # Create one task per chunk
        tasks = []
        for i in range(num_chunks):
            instance = instances[i % len(instances)]
            task = self._scrape_single_chunk(
                keyword=keyword,
                chunk_index=i,
                depth=depth_per_chunk,
                instance=instance,
                geo_coordinates=geo_coordinates,
                zoom=zoom,
                radius=radius,
                lang=lang,
                extract_emails=extract_emails,
            )
            tasks.append(task)

        # Run all chunks in parallel
        chunk_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Combine and deduplicate
        all_results = []
        successful_chunks = 0
        failed_chunks = 0

        for i, result in enumerate(chunk_results):
            if isinstance(result, Exception):
                logger.warning(
                    "go_scraper.chunk_failed",
                    chunk_index=i,
                    error=str(result)
                )
                failed_chunks += 1
            elif result:
                all_results.extend(result)
                successful_chunks += 1
            else:
                failed_chunks += 1

        # Deduplicate by name+address
        seen = set()
        unique_results = []
        for r in all_results:
            key = (
                r.get("name", "").lower().strip(),
                r.get("address", "").lower().strip()
            )
            if key not in seen and key != ("", ""):
                seen.add(key)
                unique_results.append(r)

        logger.info(
            "go_scraper.chunked_complete",
            keyword=keyword,
            total_collected=len(all_results),
            after_dedup=len(unique_results),
            successful_chunks=successful_chunks,
            failed_chunks=failed_chunks,
            total_chunks=num_chunks
        )

        return unique_results[:total_results]

    async def _clear_instance_queue(self, instance: str) -> None:
        """
        Clear pending/stuck jobs from a Go scraper instance before submitting new batch.
        
        Uses the Go scraper's own DELETE API to remove old jobs from the SQLite queue.
        This prevents stuck "pending" jobs from blocking new submissions.
        """
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                # Get all jobs on this instance
                resp = await client.get(
                    f"{instance}/api/v1/jobs",
                    headers=self._headers
                )
                
                if resp.status_code != 200:
                    return
                
                jobs = resp.json()
                if not jobs:
                    return
                
                # Delete ALL jobs (pending, working, ok, failed)
                # Old completed jobs fill up the queue and block new submissions
                deleted = 0
                for job in jobs:
                    job_id = job.get("ID") or job.get("id", "")
                    if job_id:
                        try:
                            del_resp = await client.delete(
                                f"{instance}/api/v1/jobs/{job_id}",
                                headers=self._headers
                            )
                            if del_resp.status_code in (200, 204, 404):
                                deleted += 1
                        except Exception:
                            pass
                
                if deleted > 0:
                    logger.info(
                        "go_scraper.queue_cleared",
                        instance=instance,
                        deleted_jobs=deleted
                    )
                    
        except Exception as e:
            logger.warning(
                "go_scraper.queue_clear_failed",
                instance=instance,
                error=str(e)
            )

    async def _scrape_single_chunk(
        self,
        keyword: str,
        chunk_index: int,
        depth: int,
        instance: str,
        geo_coordinates: str = "",
        zoom: int = 14,
        radius: float = 5,
        lang: str = "en",
        extract_emails: bool = False,
    ) -> list[dict]:
        """Scrape one chunk on a specific instance."""
        # PRODUCTION FIX: Increased timeouts to account for:
        # - Go scraper startup time: 2-3 minutes
        # - Processing time: 4-5 minutes for 80 results
        # - Queue delays when multiple neighborhoods are submitted
        estimated_results = min(depth * 8, 120)
        base_time = 180   # search + scroll + startup (increased from 60s)
        detail_time = estimated_results * 5  # 5s per page (increased from 3s)
        buffer = 120      # safety margin (increased from 90s)
        go_timeout = int(base_time + detail_time + buffer)
        # Increased upper limit to 1200s (20 min) to handle complex neighborhoods
        go_timeout = max(300, min(go_timeout, 1200))
        
        logger.info(
            "go_scraper.chunk_timeout_calculated",
            chunk_index=chunk_index,
            estimated_results=estimated_results,
            timeout_seconds=go_timeout
        )

        lat, lon = "", ""
        if geo_coordinates:
            parts = geo_coordinates.split(",")
            if len(parts) == 2:
                lat = parts[0].strip()
                lon = parts[1].strip()

        payload = {
            "name": f"chunk-{chunk_index}-{keyword[:30]}",
            "keywords": [keyword],
            "lang": lang,
            "zoom": zoom,
            "depth": depth,
            "fast_mode": False,
            "email": extract_emails,
            "radius": int(radius * 1000) if radius > 0 else 10000,
            "max_time": go_timeout,  # Go scraper expects "max_time", not "timeout"
            "lat": lat,
            "lon": lon,
        }

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                job_id = await self._submit_job(client, payload, instance)
                if not job_id:
                    logger.warning(
                        "go_scraper.chunk_submit_failed",
                        chunk_index=chunk_index,
                        instance=instance
                    )
                    return []

                logger.info(
                    "go_scraper.chunk_submitted",
                    chunk_index=chunk_index,
                    job_id=job_id,
                    instance=instance
                )

                job_data = await self._poll_until_done(
                    client, job_id, keyword, go_timeout, instance
                )

                if job_data:
                    status = (
                        job_data.get("Status") or
                        job_data.get("status", "")
                    )
                    if status in ("ok", "working"):
                        results = await self._download_and_parse(
                            job_id, keyword, instance
                        )
                        logger.info(
                            "go_scraper.chunk_complete",
                            chunk_index=chunk_index,
                            result_count=len(results or []),
                            instance=instance
                        )
                        return results or []

                return []

        except Exception as e:
            logger.warning(
                "go_scraper.chunk_error",
                chunk_index=chunk_index,
                instance=instance,
                error=str(e)
            )
            return []

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _submit_job(self, client: httpx.AsyncClient, payload: dict, base_url: str) -> Optional[str]:
        """POST /api/v1/jobs and return the job id string."""
        try:
            resp = await client.post(
                f"{base_url}/api/v1/jobs",
                json=payload,
                headers=self._headers,
            )
            if resp.status_code not in (200, 201, 202):
                logger.error(
                    "go_scraper.submit_failed",
                    status=resp.status_code,
                    body=resp.text[:500],
                    instance=base_url
                )
                return None
            data = resp.json()
            # Web mode returns {"id": "<uuid>"}
            return data.get("id")
        except Exception as e:
            logger.error("go_scraper.submit_error", error=str(e), instance=base_url)
            return None

    async def _poll_until_done(
        self, client: httpx.AsyncClient, job_id: str, keyword: str, max_time_seconds: int = None, base_url: str = None
    ) -> Optional[dict]:
        """
        Poll GET /api/v1/jobs/{id} until status is 'ok' or 'failed'.
        
        Args:
            max_time_seconds: Override the default timeout with the job's max_time + buffer
        """
        # Use job-specific timeout if provided, otherwise use default
        # Add 300 second buffer to allow for:
        # - Browser download on fresh containers (2-3 min)
        # - Go scraper startup time (~30s)
        # - Status reporting after completion
        timeout = (max_time_seconds + 300) if max_time_seconds else self.timeout
        deadline = time.time() + timeout
        attempt = 0

        logger.info(
            "go_scraper.poll_start",
            job_id=job_id,
            timeout=timeout,
            max_time_seconds=max_time_seconds,
            instance=base_url
        )

        while time.time() < deadline:
            attempt += 1
            try:
                resp = await client.get(
                    f"{base_url}/api/v1/jobs/{job_id}",
                    headers=self._headers,
                )
                if resp.status_code == 404:
                    # Job was deleted from Go scraper SQLite (cleanup task or auto-delete
                    # after completion). Treat as completed - attempt to download CSV.
                    logger.warning(
                        "go_scraper.job_not_found_attempting_download",
                        job_id=job_id,
                        attempt=attempt,
                        instance=base_url,
                        message="Job 404 - may have completed and been cleaned up, trying CSV download"
                    )
                    # Return a synthetic "ok" response so caller attempts download
                    return {"Status": "ok", "id": job_id}

                if resp.status_code != 200:
                    logger.warning(
                        "go_scraper.poll_error",
                        job_id=job_id,
                        status=resp.status_code,
                        instance=base_url
                    )
                    await asyncio.sleep(self.poll_interval)
                    continue

                data = resp.json()
                status = data.get("Status") or data.get("status", "")

                logger.debug(
                    "go_scraper.poll",
                    job_id=job_id,
                    status=status,
                    attempt=attempt,
                )

                # Web mode statuses: pending → working → ok | failed
                if status == "ok":
                    logger.info(
                        "go_scraper.job_completed",
                        job_id=job_id,
                        keyword=keyword,
                        instance=base_url
                    )
                    return data

                if status == "failed":
                    logger.warning(
                        "go_scraper.job_failed",
                        job_id=job_id,
                        status=status,
                        instance=base_url
                    )
                    return None

            except Exception as e:
                logger.warning("go_scraper.poll_exception", job_id=job_id, error=str(e), instance=base_url)

            await asyncio.sleep(self.poll_interval)

        logger.warning(
            "go_scraper.poll_timeout",
            job_id=job_id,
            keyword=keyword,
            timeout=timeout,
            instance=base_url,
            message="Timeout — attempting partial download"
        )
        try:
            resp = await client.get(
                f"{base_url}/api/v1/jobs/{job_id}",
                headers=self._headers,
            )
            if resp.status_code == 200:
                job_data = resp.json()
                current_status = (
                    job_data.get("Status") or
                    job_data.get("status", "")
                )
                logger.info(
                    "go_scraper.timeout_status_check",
                    job_id=job_id,
                    status=current_status,
                    message="Downloading partial results"
                )
                if current_status in ("ok", "working"):
                    return job_data
        except Exception as e:
            logger.warning(
                "go_scraper.timeout_download_failed",
                job_id=job_id,
                error=str(e)
            )
        return None

    async def _download_and_parse(self, job_id: str, keyword: str, base_url: str) -> list[dict]:
        """Download the CSV result file and parse into standard dicts."""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(
                    f"{base_url}/api/v1/jobs/{job_id}/download",
                    headers=self._headers,
                )
                if resp.status_code != 200:
                    logger.warning(
                        "go_scraper.download_failed",
                        job_id=job_id,
                        status=resp.status_code,
                        body=resp.text[:200],
                        instance=base_url
                    )
                    return []

                csv_text = resp.text
                if not csv_text.strip():
                    logger.warning("go_scraper.empty_csv", job_id=job_id)
                    return []

                logger.debug(
                    "go_scraper.csv_received",
                    job_id=job_id,
                    size=len(csv_text),
                    first_line=csv_text.split('\n')[0][:200] if csv_text else "",
                )

                reader = csv.DictReader(io.StringIO(csv_text))
                results = []
                for idx, row in enumerate(reader):
                    mapped = self._map_csv_row(row)
                    if mapped.get("name"):
                        results.append(mapped)
                    else:
                        logger.debug(
                            "go_scraper.row_skipped",
                            job_id=job_id,
                            row_index=idx,
                            title=row.get("title", "")[:50],
                        )

                logger.info(
                    "go_scraper.csv_parsed",
                    job_id=job_id,
                    keyword=keyword,
                    row_count=len(results),
                )
                return results

        except Exception as e:
            logger.error("go_scraper.download_error", job_id=job_id, error=str(e), exc_info=True)
            return []

    # ------------------------------------------------------------------
    # Field mapping: CSV row → Python standard format
    # ------------------------------------------------------------------

    def _map_csv_row(self, row: dict) -> dict:
        """
        Map a Go scraper CSV row to the Python backend's standard result format.

        Go CSV columns (from gmaps package):
          input_id, link, title, category, address, open_hours, open_now,
          plus_code, review_count, review_rating, reviews_per_rating,
          latitude, longitude, cid, place_id, data_id, images_count,
          thumbnail, images, owner_name, owner_id, complete_address, about,
          user_reviews, description, emails, phone, web_site, timezone,
          price_range, status, reservations, order_online, menu
        """
        # Helper to safely get float
        def _float(val: str) -> Optional[float]:
            try:
                return float(val) if val and val.strip() else None
            except (ValueError, TypeError):
                return None

        # Helper to safely get int
        def _int(val: str) -> Optional[int]:
            try:
                return int(val) if val and val.strip() else None
            except (ValueError, TypeError):
                return None

        result: dict = {
            # Identity
            "name": row.get("title", "").strip() or row.get("name", "").strip(),
            "category": row.get("category", "").strip(),

            # Location
            "address": row.get("address", "").strip(),
            "latitude": _float(row.get("latitude", "")),
            "longitude": _float(row.get("longitude", "")),

            # Contact
            "phone_primary": row.get("phone", "").strip(),
            "website": row.get("web_site", "").strip(),
            "email": self._first_email(row.get("emails", "")),

            # Reviews
            "rating_overall": _float(row.get("review_rating", "")),
            "review_count": _int(row.get("review_count", "")),

            # Media
            "thumbnail_url": row.get("thumbnail", "").strip(),
            "image_urls": self._parse_images(row.get("images", "")),
            "image_count": _int(row.get("images_count", "")),

            # Business
            "business_status": row.get("status", "").strip(),
            "description_short": row.get("description", "").strip(),
            "price_range_label": row.get("price_range", "").strip(),

            # Source tracking
            "source_url": row.get("link", "").strip(),
            "scraper_source": "go_scraper",
        }

        # Opening hours
        open_hours = row.get("open_hours", "").strip()
        if open_hours:
            result["opening_hours"] = open_hours

        # Extra data: store rich fields as JSONB
        result["extra_data"] = self._build_extra_data(row)

        return result

    def _build_extra_data(self, row: dict) -> dict:
        """Build extra_data dict with Go-specific rich fields."""
        extra: dict = {}

        for key in ("place_id", "data_id", "cid", "plus_code", "link",
                    "reviews_link", "timezone", "owner_name", "owner_id"):
            val = row.get(key, "").strip()
            if val:
                extra[key] = val

        reviews_per_rating = row.get("reviews_per_rating", "").strip()
        if reviews_per_rating:
            extra["reviews_per_rating"] = reviews_per_rating

        about = row.get("about", "").strip()
        if about:
            extra["about"] = about

        user_reviews = row.get("user_reviews", "").strip()
        if user_reviews:
            extra["user_reviews"] = user_reviews

        images_count = row.get("images_count", "").strip()
        if images_count:
            try:
                extra["images_count"] = int(images_count)
            except ValueError:
                pass
        
        # Store raw images string in extra_data for reference
        images = row.get("images", "").strip()
        if images:
            extra["images"] = images

        reservations = row.get("reservations", "").strip()
        if reservations:
            extra["reservations"] = reservations

        order_online = row.get("order_online", "").strip()
        if order_online:
            extra["order_online"] = order_online

        menu = row.get("menu", "").strip()
        if menu:
            extra["menu"] = menu

        complete_address = row.get("complete_address", "").strip()
        if complete_address:
            extra["complete_address"] = complete_address

        return extra

    @staticmethod
    def _first_email(emails_str: str) -> Optional[str]:
        """Return the first email from a comma-separated string, or None."""
        if not emails_str:
            return None
        emails_str = emails_str.strip()
        if not emails_str:
            return None
        parts = [e.strip() for e in emails_str.split(",") if e.strip()]
        return parts[0] if parts else None

    @staticmethod
    def _parse_images(images_str: str) -> Optional[list[str]]:
        """
        Parse images field from Go scraper CSV.
        
        The images field is a JSON array of objects with format:
        [{"title":"All","image":"https://..."},{"title":"Room","image":"https://..."},...]
        
        Returns list of image URLs or None if empty.
        """
        if not images_str or not images_str.strip():
            return None
        
        images_str = images_str.strip()
        
        # Parse JSON array of image objects
        if images_str.startswith('['):
            try:
                import json
                image_objects = json.loads(images_str)
                if isinstance(image_objects, list) and image_objects:
                    # Extract 'image' field from each object
                    urls = []
                    for obj in image_objects:
                        if isinstance(obj, dict) and 'image' in obj:
                            url = obj['image']
                            if url and url.strip():
                                urls.append(url.strip())
                        elif isinstance(obj, str):  # Fallback: plain string array
                            if obj and obj.strip():
                                urls.append(obj.strip())
                    return urls if urls else None
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning("go_scraper.images_parse_error", error=str(e), images_preview=images_str[:100])
                pass
        
        # Fallback: try comma-separated URLs
        if ',' in images_str:
            urls = [url.strip() for url in images_str.split(',') if url.strip()]
            return urls if urls else None
        
        # Single URL
        return [images_str] if images_str else None
