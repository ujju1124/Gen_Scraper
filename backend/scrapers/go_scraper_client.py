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
            # Email extraction: 15 seconds per result + 300s base (more generous)
            max_time_seconds = 300 + (estimated_results * 15)
            # Cap at 1200 seconds (20 minutes) for email extraction jobs
            max_time_seconds = max(300, min(max_time_seconds, 1200))
        else:
            # No email extraction: 5 seconds per result + 300s base (more generous)
            max_time_seconds = 300 + (estimated_results * 5)
            # Cap at 900 seconds (15 minutes) for non-email jobs
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
            "max_time": max_time_seconds,  # seconds (Go converts to Duration)
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
        # Add 60 second buffer to allow Go scraper to finish and report status
        timeout = (max_time_seconds + 60) if max_time_seconds else self.timeout
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
            timeout=timeout,  # Log the actual timeout used, not self.timeout
            instance=base_url,
            message="Timeout reached - will attempt to download partial results"
        )
        # Return the job data even though it timed out - it might have partial results
        # The caller will check if there are any results to download
        try:
            resp = await client.get(
                f"{base_url}/api/v1/jobs/{job_id}",
                headers=self._headers,
            )
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            logger.warning("go_scraper.timeout_status_check_failed", job_id=job_id, error=str(e))
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
