"""
Google Maps Scraper — Go-first with Playwright fallback

Scraping strategy (in order):
  1. Go scraper microservice (port 8080) — 33+ fields, fast, rich data
  2. Playwright fallback — original browser-based scraper (12 fields)

The Go scraper is tried first. If it's unreachable, disabled, or returns 0
results, the Playwright-based scraper runs as a fallback so no job ever fails
silently.
"""

import re
import structlog
from typing import Optional
from sqlalchemy.orm import Session

from config import settings
from models.source import Source
from scrapers.base_scraper import BaseScraper
from scrapers.go_scraper_client import GoScraperClient

logger = structlog.get_logger()

# City → geo_coordinates lookup for common Nepal cities
# Used when the job doesn't supply explicit coordinates
CITY_COORDINATES = {
    "kathmandu":  "27.693444,85.281924",
    "pokhara":    "28.209538,83.985567",
    "lalitpur":   "27.666667,85.316667",
    "bhaktapur":  "27.671667,85.428889",
    "chitwan":    "27.529722,84.354167",
    "bharatpur":  "27.683333,84.433333",
    "biratnagar": "26.455000,87.283333",
    "birgunj":    "27.012222,84.877778",
    "dharan":     "26.812222,87.283333",
    "butwal":     "27.700556,83.448056",
    "hetauda":    "27.426944,85.031944",
    "janakpur":   "26.727778,85.926389",
    "nepalgunj":  "28.050000,81.616667",
    "dhangadhi":  "28.694444,80.594444",
}


class GoogleMapsScraper(BaseScraper):
    """
    Google Maps scraper — Go microservice first, Playwright fallback.

    This is the universal source that runs for all job categories.
    """

    def __init__(self, source_name: str = "google_maps"):
        super().__init__()
        self.source_name = source_name
        self._go_client = GoScraperClient()

    async def run(
        self,
        source: Source,
        db: Session,
        location: str,
        max_results: Optional[int] = None,
        category_id: Optional[int] = None,
    ) -> list[dict]:
        """
        Override BaseScraper.run() to try Go scraper before opening a browser.

        Falls back to Playwright only if Go scraper is unavailable or returns 0.
        """
        logger.info(
            "google_maps.run_start",
            location=location,
            max_results=max_results,
            go_enabled=settings.GO_SCRAPER_ENABLED,
        )
        
        # DEBUG: Force log to see if this code path is reached
        print(f"[DEBUG] google_maps.run() called - location={location}, go_enabled={settings.GO_SCRAPER_ENABLED}")
        logger.info("DEBUG_RUN_CALLED", location=location, go_enabled=settings.GO_SCRAPER_ENABLED)

        # ── Tier 1: Go scraper ──────────────────────────────────────────
        if settings.GO_SCRAPER_ENABLED:
            results = await self._run_go_scraper(
                source, db, location, max_results, category_id
            )
            if results:
                # Check if we got all requested results or just partial
                got_all_results = not max_results or len(results) >= max_results
                
                if got_all_results:
                    logger.info(
                        "google_maps.go_scraper_succeeded",
                        location=location,
                        result_count=len(results),
                        status="complete"
                    )
                    return results
                else:
                    # Got partial results - use Playwright to complete
                    logger.warning(
                        "google_maps.go_scraper_partial",
                        location=location,
                        partial_count=len(results),
                        requested=max_results,
                        message="Got partial results from Go scraper - using Playwright to complete"
                    )
                    # Store partial results to combine later
                    go_scraper_results = results
            else:
                logger.warning(
                    "google_maps.go_scraper_returned_empty",
                    location=location,
                    message="Falling back to Playwright scraper",
                )
                go_scraper_results = []

        # ── Tier 2: Playwright fallback ─────────────────────────────────
        logger.info("google_maps.playwright_fallback_start", location=location)
        
        # Update progress: Starting Playwright fallback
        from models.scrape_job import ScrapeJob
        job = db.query(ScrapeJob).filter(
            ScrapeJob.location == location,
            ScrapeJob.category_id == category_id,
            ScrapeJob.status == "RUNNING"
        ).order_by(ScrapeJob.started_at.desc()).first()
        
        if job:
            if go_scraper_results:
                job.scraping_progress = f"🌐 Completing with browser scraper ({len(go_scraper_results)} already found)..."
            else:
                job.scraping_progress = f"🌐 Using browser scraper for {location}..."
            db.commit()
            db.refresh(job)
        
        # Calculate remaining results needed
        remaining_needed = None
        if max_results and go_scraper_results:
            remaining_needed = max(0, max_results - len(go_scraper_results))
            logger.info(
                "google_maps.playwright_remaining",
                location=location,
                already_have=len(go_scraper_results),
                remaining_needed=remaining_needed
            )
        
        # Resolve category for neighborhood-aware fallback
        category = await self._resolve_category(db, category_id)
        
        # Use neighborhood-aware Playwright fallback to avoid cross-city contamination
        playwright_results = await self._run_playwright_with_neighborhoods(
            source=source,
            db=db,
            location=location,
            category=category,
            max_results=remaining_needed or max_results,
            category_id=category_id
        )
        
        # Combine results: Go scraper + Playwright
        if go_scraper_results and playwright_results:
            # Deduplicate by name+address to avoid duplicates
            seen = set()
            combined_results = []
            
            for result in go_scraper_results + playwright_results:
                # Skip None results
                if result is None:
                    logger.warning("google_maps.none_result_skipped", location=location)
                    continue
                
                # Safely get name and address with None handling
                name = result.get("name") or ""
                address = result.get("address") or ""
                key = (name.lower(), address.lower())
                
                if key not in seen and key != ("", ""):
                    seen.add(key)
                    combined_results.append(result)
            
            logger.info(
                "google_maps.results_combined",
                location=location,
                go_scraper_count=len(go_scraper_results),
                playwright_count=len(playwright_results),
                combined_count=len(combined_results),
                duplicates_removed=len(go_scraper_results) + len(playwright_results) - len(combined_results)
            )
            
            results = combined_results
        elif go_scraper_results:
            results = go_scraper_results
        else:
            results = playwright_results
        
        # Apply geographic filtering to remove results from wrong city
        from scrapers.geo_filter import filter_results_by_city
        
        original_count = len(results)
        results, removed = filter_results_by_city(
            results=results,
            city=location,
            strict=False  # Keep results without coords
        )
        
        # Always log geographic filtering for visibility
        logger.info(
            "google_maps.geo_filtered",
            location=location,
            original=original_count,
            after_filter=len(results),
            removed=removed,
            message=f"Geographic filtering: {removed} removed, {len(results)} kept"
        )
        
        # Update progress: Completed
        if job and results:
            job.scraping_progress = f"✅ Found {len(results)} results total"
            db.commit()
            db.refresh(job)
        
        return results

    # ------------------------------------------------------------------
    # Go scraper tier
    # ------------------------------------------------------------------

    async def _run_go_scraper(
        self,
        source: Source,
        db: Session,
        location: str,
        max_results: Optional[int],
        category_id: Optional[int],
    ) -> list[dict]:
        """Call the Go scraper API and return mapped results."""
        # Resolve category name for keyword
        category = await self._resolve_category(db, category_id)

        # Build keyword
        keyword = f"{category} in {location}"

        # Try to get google_maps_settings from the current job
        # The job is not directly passed, so we need to query it from the session
        # We can identify the job by looking for a RUNNING job with this location and category
        from models.scrape_job import ScrapeJob
        job = db.query(ScrapeJob).filter(
            ScrapeJob.location == location,
            ScrapeJob.category_id == category_id,
            ScrapeJob.status == "RUNNING"
        ).order_by(ScrapeJob.started_at.desc()).first()

        # Update progress: Starting Go scraper
        if job:
            job.scraping_progress = f"🔍 Searching Google Maps for {category} in {location}..."
            db.commit()
            db.refresh(job)  # Refresh to ensure the change is visible to other sessions

        # Extract settings from job or use defaults
        settings_dict = job.google_maps_settings if job and job.google_maps_settings else {}
        
        # Resolve geo_coordinates from settings or city name
        geo_coordinates = settings_dict.get("geo_coordinates") or self._get_geo_coordinates(location)

        # Derive max_depth from settings or max_results
        # The Go scraper now scrolls until no more results are found (3 consecutive scrolls with no change)
        # maxDepth is just a safety limit to prevent infinite scrolling
        # We set it very high so the "no more results" detection kicks in first
        max_depth = settings_dict.get("max_depth")
        if max_depth is None:
            if max_results:
                # Set maxDepth high enough to never hit the limit
                # The Go scraper will stop automatically when no more results load
                # Google Maps limit is ~120 results per search anyway
                
                if max_results <= 25:
                    # Small requests: depth 10 is plenty
                    # Google Maps loads ~20 results per scroll
                    max_depth = 10
                elif max_results <= 50:
                    # Small-medium requests: use depth 20
                    max_depth = 20
                elif max_results <= 100:
                    # Large requests: use depth 50
                    max_depth = 50
                else:
                    # Very large requests: use max depth 80
                    max_depth = 80
                
                logger.info(
                    "google_maps.max_depth_calculated",
                    max_results=max_results,
                    max_depth=max_depth,
                    note="Go scraper will auto-stop when no more results load (3 consecutive scrolls with no change)"
                )
            else:
                # For unlimited scraping (max_results=None), use max depth
                # Will scrape until Google's ~120 result limit or no more results
                max_depth = 100
                logger.info(
                    "google_maps.max_depth_unlimited",
                    max_depth=max_depth,
                    note="Will scrape until no more results load (up to Google's ~120 limit)"
                )

        # Get other settings with defaults
        zoom = settings_dict.get("zoom", 14)
        radius = settings_dict.get("radius", 0)
        lang = settings_dict.get("lang", "en")
        extract_emails = settings_dict.get("extract_emails", False)
        extra_reviews = settings_dict.get("extra_reviews", False)
        fast_mode = settings_dict.get("fast_mode", False)

        logger.info(
            "google_maps.go_scraper_call",
            keyword=keyword,
            geo_coordinates=geo_coordinates,
            max_depth=max_depth,
            zoom=zoom,
            radius=radius,
            max_results=max_results,
        )

        CHUNK_THRESHOLD = 150
        
        # DEBUG: Log routing decision
        logger.info(
            "google_maps.routing_decision",
            max_results=max_results,
            threshold=CHUNK_THRESHOLD,
            will_use_large=bool(max_results and max_results > CHUNK_THRESHOLD),
            location=location,
            keyword=keyword
        )
        
        # Use neighborhood search or chunking for large jobs (>150 results)
        if max_results and max_results > CHUNK_THRESHOLD:
            logger.info(
                "go_scraper.using_large_job_strategy",
                max_results=max_results,
                keyword=keyword,
                location=location,
                reason=f"Large job (>{CHUNK_THRESHOLD} results) - using neighborhood search or chunking"
            )
            results = await self._go_client.scrape_large(
                keyword=keyword,
                total_results=max_results,
                location=location,
                geo_coordinates=geo_coordinates,
                zoom=zoom,
                radius=radius,
                lang=lang,
                extract_emails=extract_emails,
            )
        else:
            # Single mode for small/medium jobs (≤150 results)
            logger.info(
                "go_scraper.using_single_mode",
                max_results=max_results,
                keyword=keyword,
                reason=f"Small/medium job (≤{CHUNK_THRESHOLD} results) - using single mode"
            )
            results = await self._go_client.scrape(
                keyword=keyword,
                geo_coordinates=geo_coordinates,
                zoom=zoom,
                max_depth=max_depth,
                radius=radius,
                lang=lang,
                extract_emails=extract_emails,
                extra_reviews=extra_reviews,
                fast_mode=fast_mode,
            )

        # Update progress: Go scraper completed
        if job and results:
            job.scraping_progress = f"✅ Google Maps found {len(results)} {category}"
            db.commit()
            db.refresh(job)  # Refresh to ensure the change is visible to other sessions
        elif job and not results:
            job.scraping_progress = "⚠️ Go scraper timed out, using Playwright fallback..."
            db.commit()
            db.refresh(job)  # Refresh to ensure the change is visible to other sessions

        # Filter results by distance from target coordinates (if available)
        original_count = len(results)
        if geo_coordinates and results:
            results = self._filter_by_distance(results, geo_coordinates, max_distance_km=50)
            if len(results) < original_count:
                logger.info(
                    "google_maps.location_filtered",
                    keyword=keyword,
                    original_count=original_count,
                    filtered_count=len(results),
                    removed_count=original_count - len(results),
                    max_distance_km=50,
                )

        # Inject city and source_id into each result
        for r in results:
            r["city"] = r.get("city_from_go") or location
            r["source_id"] = source.id
            # Remove internal helper key
            r.pop("city_from_go", None)

        # Trim to max_results if needed
        if max_results and len(results) > max_results:
            results = results[:max_results]

        return results

    async def _run_playwright_with_neighborhoods(
        self,
        source: Source,
        db: Session,
        location: str,
        category: str,
        max_results: int,
        category_id: int
    ) -> list[dict]:
        """
        Playwright fallback that uses neighborhood keywords to avoid cross-city contamination.
        
        Instead of searching "restaurants in Bhaktapur" (which returns nearby Kathmandu results),
        this searches "restaurants in Durbar Square, Bhaktapur" for each neighborhood.
        """
        from scrapers.go_scraper_client import NEIGHBORHOOD_KEYWORDS
        
        neighborhoods = NEIGHBORHOOD_KEYWORDS.get(location.lower(), [])
        
        if not neighborhoods:
            # Unknown city - use standard search but filter results afterward
            logger.info(
                "playwright.no_neighborhoods",
                location=location,
                message="No neighborhoods defined, using standard search"
            )
            return await super().run(source, db, location, max_results, category_id)
        
        # Use first 2-3 neighborhoods for Playwright (Playwright is slower, don't use all)
        max_neighborhoods = min(3, len(neighborhoods))
        selected = neighborhoods[:max_neighborhoods]
        
        logger.info(
            "playwright.neighborhood_search",
            location=location,
            total_neighborhoods=len(neighborhoods),
            selected_neighborhoods=selected,
            max_results=max_results
        )
        
        all_results = []
        seen_keys = set()  # Track (name, address) to avoid duplicates
        
        for neighborhood in selected:
            if len(all_results) >= max_results:
                break
            
            # Use neighborhood-specific keyword
            neighborhood_location = f"{neighborhood}, {location}"
            remaining = max_results - len(all_results)
            
            logger.info(
                "playwright.searching_neighborhood",
                neighborhood=neighborhood,
                location=location,
                remaining=remaining
            )
            
            try:
                # Call parent's run() method which will use _scrape()
                results = await super().run(
                    source,
                    db,
                    neighborhood_location,
                    min(remaining, 30),  # Small batches per neighborhood
                    category_id
                )
                
                # Deduplicate results
                for result in results:
                    if result is None:
                        continue
                    
                    name = result.get("name") or ""
                    address = result.get("address") or ""
                    key = (name.lower(), address.lower())
                    
                    if key not in seen_keys and key != ("", ""):
                        seen_keys.add(key)
                        all_results.append(result)
                
                logger.info(
                    "playwright.neighborhood_complete",
                    neighborhood=neighborhood,
                    results_found=len(results),
                    total_unique=len(all_results)
                )
                
            except Exception as e:
                logger.warning(
                    "playwright.neighborhood_failed",
                    neighborhood=neighborhood,
                    error=str(e)
                )
                continue
        
        logger.info(
            "playwright.neighborhood_search_complete",
            location=location,
            neighborhoods_searched=len(selected),
            total_results=len(all_results)
        )
        
        return all_results[:max_results]

    # ------------------------------------------------------------------
    # Playwright fallback tier (original implementation)
    # ------------------------------------------------------------------

    async def _scrape(
        self,
        page,
        source: Source,
        db: Session,
        location: str,
        max_results: Optional[int] = None,
        category_id: Optional[int] = None,
    ) -> list[dict]:
        """
        Original Playwright-based Google Maps scraper (fallback).
        Returns 12 standard fields.
        """
        logger.info(
            "google_maps.playwright_scrape_start",
            location=location,
            max_results=max_results,
            category_id=category_id,
        )

        category = await self._resolve_category(db, category_id)

        search_query = f"{category} in {location}".replace(" ", "+")
        search_url = f"https://www.google.com/maps/search/{search_query}/"

        logger.info("google_maps.navigating", url=search_url, category=category)

        try:
            await page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(5000)

            if await self._detect_captcha(page):
                logger.warning("google_maps.captcha_detected_early")
                return []

            result_urls = await self._scroll_and_collect_urls(page, max_results)

            if not result_urls:
                logger.warning("google_maps.no_results", location=location, category=category)
                return []

            logger.info("google_maps.urls_collected", count=len(result_urls))

            results = await self._extract_from_detail_pages(
                page, source, db, result_urls, location, category, max_results
            )

            # Tag as playwright source
            for r in results:
                r["scraper_source"] = "playwright"

            logger.info(
                "google_maps.playwright_scrape_complete",
                location=location,
                result_count=len(results),
            )
            return results

        except Exception as e:
            logger.error(
                "google_maps.playwright_scrape_error",
                location=location,
                error=str(e),
                exc_info=True,
            )
            await self._debug_page(page, "google_maps_error")
            return []

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    async def _resolve_category(self, db: Session, category_id: Optional[int]) -> str:
        """Resolve category name from category_id."""
        category = "businesses"
        if category_id:
            try:
                from models.category import Category
                cat = db.query(Category).filter(Category.id == category_id).first()
                if cat:
                    category = cat.name
            except Exception as e:
                logger.warning("google_maps.category_lookup_failed", error=str(e))
        return category

    @staticmethod
    def _get_geo_coordinates(location: str) -> str:
        """Return lat,lon string for a city name, or empty string if unknown."""
        if not location:
            return ""
        return CITY_COORDINATES.get(location.lower().strip(), "")

    @staticmethod
    def _filter_by_distance(results: list[dict], geo_coordinates: str, max_distance_km: float = 50) -> list[dict]:
        """
        Filter results by distance from target coordinates.
        
        Removes results that are more than max_distance_km away from the target.
        Uses Haversine formula for distance calculation.
        """
        if not geo_coordinates or not results:
            return results
        
        try:
            target_lat, target_lon = map(float, geo_coordinates.split(","))
        except (ValueError, AttributeError):
            logger.warning("google_maps.invalid_geo_coordinates", geo_coordinates=geo_coordinates)
            return results
        
        from math import radians, sin, cos, sqrt, atan2
        
        def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
            """Calculate distance in km between two lat/lon points."""
            R = 6371  # Earth radius in km
            
            lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
            dlat = lat2 - lat1
            dlon = lon2 - lon1
            
            a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
            c = 2 * atan2(sqrt(a), sqrt(1-a))
            
            return R * c
        
        filtered = []
        for r in results:
            lat = r.get("latitude")
            lon = r.get("longitude")
            
            if lat is None or lon is None:
                # Keep results without coordinates
                filtered.append(r)
                continue
            
            try:
                distance = haversine_distance(target_lat, target_lon, float(lat), float(lon))
                if distance <= max_distance_km:
                    filtered.append(r)
                else:
                    logger.debug(
                        "google_maps.result_filtered_by_distance",
                        name=r.get("name", "")[:50],
                        distance_km=round(distance, 2),
                        max_distance_km=max_distance_km,
                    )
            except (ValueError, TypeError) as e:
                # Keep results with invalid coordinates
                logger.warning("google_maps.distance_calc_error", error=str(e), result=r.get("name", "")[:50])
                filtered.append(r)
        
        return filtered

    # ------------------------------------------------------------------
    # Playwright helpers (unchanged from original)
    # ------------------------------------------------------------------

    async def _scroll_and_collect_urls(
        self, page, max_results: Optional[int]
    ) -> list[str]:
        feed_selector = '[role="feed"]'
        try:
            await page.wait_for_selector(feed_selector, timeout=15000)
        except Exception as e:
            logger.warning("google_maps.feed_not_found", error=str(e))
            return []

        result_urls = []
        seen_urls = set()
        last_height = 0
        scroll_attempts = 0
        max_scroll_attempts = 50

        while scroll_attempts < max_scroll_attempts:
            if max_results and len(result_urls) >= max_results:
                break

            try:
                card_elements = await page.query_selector_all("a.hfpxzc")
                for card in card_elements:
                    href = await card.get_attribute("href")
                    if href and href not in seen_urls:
                        seen_urls.add(href)
                        result_urls.append(href)
            except Exception as e:
                logger.warning("google_maps.url_collection_error", error=str(e))

            try:
                feed = await page.query_selector(feed_selector)
                if feed:
                    current_height = await page.evaluate("(el) => el.scrollHeight", feed)
                    await page.evaluate("(el) => el.scrollTo(0, el.scrollHeight)", feed)
                    await page.wait_for_timeout(3000)
                    new_height = await page.evaluate("(el) => el.scrollHeight", feed)

                    if new_height == last_height:
                        end_element = await page.query_selector(".PbZDve")
                        if end_element:
                            break
                        try:
                            await page.evaluate(
                                "() => { const c = document.querySelectorAll('a.hfpxzc'); if (c.length) c[c.length-1].click(); }"
                            )
                            await page.wait_for_timeout(2000)
                        except Exception:
                            pass

                    last_height = new_height
            except Exception as e:
                logger.warning("google_maps.scroll_error", error=str(e))
                break

            scroll_attempts += 1

        if max_results and len(result_urls) > max_results:
            result_urls = result_urls[:max_results]

        return result_urls

    async def _extract_from_detail_pages(
        self, page, source, db, result_urls, location, category, max_results
    ) -> list[dict]:
        results = []
        for idx, url in enumerate(result_urls):
            if max_results and len(results) >= max_results:
                break
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(2000)

                if await self._detect_captcha(page):
                    logger.warning("google_maps.captcha_detected", results_collected=len(results))
                    return results

                try:
                    await page.wait_for_selector('[role="main"]', timeout=10000)
                except Exception:
                    continue

                business_data = await self._extract_business_data(
                    page, source, db, url, location, category
                )
                if business_data:
                    results.append(business_data)

                await page.wait_for_timeout(3000)
            except Exception as e:
                logger.warning("google_maps.detail_extraction_error", url=url, error=str(e))
                continue

        return results

    async def _extract_business_data(
        self, page, source, db, url, location, category
    ) -> Optional[dict]:
        try:
            try:
                main_elem = await page.wait_for_selector('[role="main"]', timeout=10000)
            except Exception:
                return None

            name = await self._extract_field_with_healing(main_elem, page, source, db, "name")
            if not name:
                return None

            address = await self._extract_field_with_healing(main_elem, page, source, db, "address")
            phone = await self._extract_field_with_healing(main_elem, page, source, db, "phone")
            rating_text = await self._extract_field_with_healing(main_elem, page, source, db, "rating")
            review_text = await self._extract_field_with_healing(main_elem, page, source, db, "review_count")
            category_label = await self._extract_field_with_healing(main_elem, page, source, db, "category_label")
            business_status = await self._extract_field_with_healing(main_elem, page, source, db, "business_status")

            rating = None
            if rating_text:
                try:
                    rating = float(rating_text.strip())
                except (ValueError, AttributeError):
                    pass

            review_count = None
            if review_text:
                match = re.search(r"([\d,]+)", review_text)
                if match:
                    try:
                        review_count = int(match.group(1).replace(",", ""))
                    except ValueError:
                        pass

            website = None
            website_selector_record = self.selectors.get("website")
            if website_selector_record:
                try:
                    website_link = await main_elem.query_selector(website_selector_record.selector)
                    if website_link:
                        website = await website_link.get_attribute("href")
                except Exception:
                    pass

            thumbnail_url = None
            try:
                thumbnail_url = await page.evaluate(
                    "() => { const img = document.querySelector('button[jsaction*=\"photo\"] img, .RZ66Rb.FgCUCc img, [data-photo-index] img'); return img ? img.src : null; }"
                )
            except Exception:
                pass

            latitude, longitude = self._parse_coordinates_from_url(url)

            return {
                "name": name,
                "address": address,
                "city": location,
                "phone_primary": phone,
                "website": website,
                "rating_overall": rating,
                "review_count": review_count,
                "thumbnail_url": thumbnail_url,
                "latitude": latitude,
                "longitude": longitude,
                "category": category_label or category,
                "business_status": business_status,
                "currency": "NPR",
                "scraper_source": "playwright",
            }

        except Exception as e:
            logger.error("google_maps.extraction_error", url=url, error=str(e))
            return None

    def _parse_coordinates_from_url(self, url: str):
        try:
            match = re.search(r"!3d(-?\d+\.?\d*)!4d(-?\d+\.?\d*)", url)
            if match:
                return float(match.group(1)), float(match.group(2))
            match = re.search(r"@(-?\d+\.\d+),(-?\d+\.\d+)", url)
            if match:
                return float(match.group(1)), float(match.group(2))
        except Exception:
            pass
        return None, None
