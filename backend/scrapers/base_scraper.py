"""
BaseScraper Abstract Class for Web Scraping Portal Phase 2

This module implements the abstract base class for all scrapers.
It provides the template method pattern with:
- AsyncCamoufox browser integration
- Anti-bot measures
- Selector loading from database
- JSON-LD extraction
- HTML hash checking for reheal triggers
- Failure handling with Sentry integration
- Structured logging
"""

import hashlib
import random
import traceback
from abc import ABC, abstractmethod
from typing import Optional
from datetime import datetime

import structlog
from sqlalchemy.orm import Session
from camoufox.async_api import AsyncCamoufox
from bs4 import BeautifulSoup

from models.source import Source
from models.scraper_selector import ScraperSelector
from scrapers.inspector import Inspector

logger = structlog.get_logger()


class BaseScraper(ABC):
    """
    Abstract base class for all scrapers.
    
    Implements the template method pattern where run() orchestrates
    the scraping workflow and subclasses implement _scrape() with
    source-specific logic.
    """
    
    # User agents for rotation
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15"
    ]
    
    def __init__(self):
        """Initialize the scraper."""
        self.source_name: Optional[str] = None
        self.selectors: dict[str, ScraperSelector] = {}
    
    async def run(self, source: Source, db: Session, location: str, max_results: Optional[int] = None, category_id: Optional[int] = None) -> list[dict]:
        """
        Template method that orchestrates the scraping workflow.
        
        This method:
        1. Loads selectors from database
        2. Opens AsyncCamoufox browser with anti-bot measures
        3. Calls subclass _scrape() method
        4. Checks HTML hash for reheal trigger
        5. Closes browser cleanly
        6. Resets failure counter on success
        
        Args:
            source: Source model instance
            db: SQLAlchemy database session
            location: Location string (e.g., "Kathmandu")
            max_results: Maximum number of results to collect (None = unlimited)
            category_id: Job's category ID (passed from orchestrator for universal sources)
            
        Returns:
            List of scraped result dictionaries
        """
        results = []
        
        try:
            # Emit start event
            logger.info(
                "scraper.started",
                source_id=source.id,
                source_name=source.name,
                location=location,
                max_results=max_results
            )
            
            # Step 1: Load selectors
            self._load_selectors(source.id, db)
            
            # Step 2: Open AsyncCamoufox browser with async context manager
            async with AsyncCamoufox(
                headless=True,
                os="windows",
                geoip=False
            ) as browser:
                context = await browser.new_context(
                    viewport={"width": 1366, "height": 768},
                    locale="en-US"
                )
                page = await context.new_page()
                
                try:
                    # Step 3: Apply anti-bot measures
                    await self._apply_anti_bot_measures(page)
                    
                    # Step 4: Call subclass scrape method (pass page and max_results)
                    results = await self._scrape(page, source, db, location, max_results=max_results, category_id=category_id)
                    
                    # Step 5: Check HTML hash for reheal trigger
                    await self._check_html_hash(page, source, db)
                    
                    # Step 6: Reset failure counter on success
                    source.consecutive_failure_count = 0
                    db.commit()
                    
                    logger.info(
                        "scraper.completed",
                        source_id=source.id,
                        source_name=source.name,
                        location=location,
                        result_count=len(results),
                        max_results=max_results
                    )
                    
                except Exception as e:
                    # Handle failure
                    await self._handle_failure(page, source, db, e)
                    return []
                    
                finally:
                    # Step 7: Close page and context cleanly
                    await page.close()
                    await context.close()
            
        except Exception as e:
            logger.error(
                "scraper.browser_init_failed",
                source_id=source.id,
                source_name=source.name,
                error=str(e)
            )
            return []
        
        return results
    
    @abstractmethod
    async def _scrape(self, page, source: Source, db: Session, location: str, max_results: Optional[int] = None, category_id: Optional[int] = None) -> list[dict]:
        """
        Subclass-specific scraping logic.
        
        This method must be implemented by each scraper subclass.
        It should use the page parameter to navigate and extract data.
        
        Args:
            page: Playwright page object
            source: Source model instance
            db: SQLAlchemy database session
            location: Location string (e.g., "Kathmandu")
            max_results: Maximum results to collect (None = unlimited, scrape all pages)
            category_id: Job's category ID (for universal sources like google_maps)
            
        Returns:
            List of scraped result dictionaries
        """
        pass
    
    def _load_selectors(self, source_id: int, db: Session) -> None:
        """
        Load active selectors from database.
        
        Queries scraper_selectors table filtered by source_id and is_active=TRUE.
        Stores selectors in self.selectors dict keyed by field_name.
        
        Args:
            source_id: ID of the source
            db: SQLAlchemy database session
        """
        selector_records = db.query(ScraperSelector).filter(
            ScraperSelector.source_id == source_id,
            ScraperSelector.is_active == True
        ).all()
        
        self.selectors = {
            record.field_name: record
            for record in selector_records
        }
        
        logger.debug(
            "scraper.selectors_loaded",
            source_id=source_id,
            selector_count=len(self.selectors)
        )
    
    def _extract_json_ld(self, html: str) -> dict:
        """
        Extract structured data from JSON-LD script tags.
        
        Finds all <script type="application/ld+json"> tags,
        parses JSON, and extracts relevant fields.
        
        Common JSON-LD types:
        - @type: "Hotel", "Restaurant", "LocalBusiness"
        - Fields: name, address, telephone, email, url, aggregateRating, etc.
        
        Args:
            html: Page HTML content
            
        Returns:
            Dictionary of extracted fields
        """
        import json
        
        extracted = {}
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            json_ld_scripts = soup.find_all('script', type='application/ld+json')
            
            for script in json_ld_scripts:
                try:
                    data = json.loads(script.string)
                    
                    # Extract common fields
                    if isinstance(data, dict):
                        # Name
                        if 'name' in data:
                            extracted['name'] = data['name']
                        
                        # Address
                        if 'address' in data:
                            addr = data['address']
                            if isinstance(addr, dict):
                                extracted['address'] = addr.get('streetAddress', '')
                                extracted['city'] = addr.get('addressLocality', '')
                            elif isinstance(addr, str):
                                extracted['address'] = addr
                        
                        # Contact
                        if 'telephone' in data:
                            extracted['phone_primary'] = data['telephone']
                        if 'email' in data:
                            extracted['email'] = data['email']
                        if 'url' in data:
                            extracted['website'] = data['url']
                        
                        # Rating
                        if 'aggregateRating' in data:
                            rating = data['aggregateRating']
                            if isinstance(rating, dict):
                                extracted['rating_overall'] = rating.get('ratingValue')
                                extracted['review_count'] = rating.get('reviewCount')
                        
                        # Coordinates
                        if 'geo' in data:
                            geo = data['geo']
                            if isinstance(geo, dict):
                                extracted['latitude'] = geo.get('latitude')
                                extracted['longitude'] = geo.get('longitude')
                        
                        # Price range
                        if 'priceRange' in data:
                            extracted['price_range_label'] = data['priceRange']
                        
                        # Image
                        if 'image' in data:
                            img = data['image']
                            if isinstance(img, str):
                                extracted['thumbnail_url'] = img
                            elif isinstance(img, list) and len(img) > 0:
                                extracted['thumbnail_url'] = img[0]
                        
                        # Description
                        if 'description' in data:
                            extracted['description_short'] = data['description']
                    
                except json.JSONDecodeError:
                    continue
            
            if extracted:
                logger.info(
                    "scraper.json_ld_found",
                    field_count=len(extracted),
                    fields=list(extracted.keys())
                )
            
        except Exception as e:
            logger.warning(
                "scraper.json_ld_extraction_failed",
                error=str(e)
            )
        
        return extracted
    
    async def _apply_anti_bot_measures(self, page) -> None:
        """
        Apply anti-bot detection measures.
        
        Measures:
        - Set navigator.webdriver to undefined
        - Rotate user agent
        - Set viewport to 1366×768
        - Set locale to en-US
        - Random delay 1.5-3.5 seconds
        
        Args:
            page: Playwright page object
        """
        if not page:
            return
        
        try:
            # Set navigator.webdriver to undefined
            await page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """)
            
            # Rotate user agent
            user_agent = random.choice(self.USER_AGENTS)
            await page.set_extra_http_headers({
                'User-Agent': user_agent
            })
            
            # Random delay — shorter to reduce total scrape time
            delay = random.uniform(0.5, 1.5)
            await page.wait_for_timeout(int(delay * 1000))
            
            logger.debug(
                "scraper.anti_bot_applied",
                user_agent=user_agent,
                delay=delay
            )
            
        except Exception as e:
            logger.warning(
                "scraper.anti_bot_failed",
                error=str(e)
            )
    
    async def _detect_captcha(self, page) -> bool:
        """
        Detect if page shows CAPTCHA.
        
        Checks:
        - Page title contains "captcha", "robot", "verify"
        - Iframe src contains "captcha", "recaptcha"
        - Div id/class contains "captcha", "challenge"
        
        Args:
            page: Playwright page object
            
        Returns:
            True if CAPTCHA detected, False otherwise
        """
        if not page:
            return False
        
        try:
            # Check page title
            title = (await page.title()).lower()
            if any(keyword in title for keyword in ['captcha', 'robot', 'verify', 'challenge']):
                logger.warning(
                    "scraper.captcha_detected",
                    detection_method="title",
                    title=title
                )
                return True
            
            # Check for iframe with captcha
            iframes = await page.query_selector_all('iframe')
            for iframe in iframes:
                src = await iframe.get_attribute('src')
                if src and any(keyword in src.lower() for keyword in ['captcha', 'recaptcha', 'hcaptcha']):
                    logger.warning(
                        "scraper.captcha_detected",
                        detection_method="iframe",
                        src=src
                    )
                    return True
            
            # Check for div with captcha class/id
            html = await page.content()
            if any(keyword in html.lower() for keyword in ['id="captcha"', 'class="captcha"', 'recaptcha', 'hcaptcha']):
                logger.warning(
                    "scraper.captcha_detected",
                    detection_method="html_content"
                )
                return True
            
        except Exception as e:
            logger.warning(
                "scraper.captcha_detection_failed",
                error=str(e)
            )
        
        return False
    
    async def _check_html_hash(self, page, source: Source, db: Session) -> None:
        """
        Check if page HTML has changed (trigger for reheal).
        
        Computes SHA-256 of page HTML and compares to stored hash
        in scraper_selectors. If mismatch, triggers reheal via Inspector.
        
        Args:
            page: Playwright page object
            source: Source model instance
            db: SQLAlchemy database session
        """
        if not page:
            return
        
        try:
            # Get page HTML
            html = await page.content()
            
            # Compute hash
            current_hash = hashlib.sha256(html.encode()).hexdigest()
            
            # Check against stored hashes
            for field_name, selector_record in self.selectors.items():
                stored_hash = selector_record.html_snapshot_hash
                
                if stored_hash and stored_hash != current_hash:
                    logger.warning(
                        "scraper.html_hash_mismatch",
                        source_id=source.id,
                        field_name=field_name,
                        stored_hash=stored_hash[:8],
                        current_hash=current_hash[:8]
                    )
                    
                    # Trigger reheal if AUTO mode
                    if source.heal_mode == "AUTO":
                        inspector = Inspector(db)
                        new_selector = await inspector.heal(
                            page,
                            source.id,
                            field_name
                        )
                        
                        if new_selector:
                            # Update selector in memory
                            self.selectors[field_name].selector = new_selector
            
        except Exception as e:
            logger.warning(
                "scraper.html_hash_check_failed",
                error=str(e)
            )
    
    async def _debug_page(self, page, step_name: str) -> None:
        """Save screenshot and HTML for debugging (only in development)."""
        try:
            import os
            from datetime import datetime
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            debug_dir = "/app/debug"
            os.makedirs(debug_dir, exist_ok=True)
            
            screenshot_path = f"{debug_dir}/debug_{step_name}_{timestamp}.png"
            html_path = f"{debug_dir}/debug_{step_name}_{timestamp}.html"
            
            await page.screenshot(path=screenshot_path, full_page=False)
            html = await page.content()
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html)
            
            logger.debug(
                "scraper.debug_saved",
                step=step_name,
                screenshot=screenshot_path,
                html=html_path
            )
        except Exception as e:
            logger.warning("scraper.debug_failed", error=str(e))
    
    async def _handle_failure(self, page, source: Source, db: Session, exception: Exception) -> None:
        """
        Handle scraper failure.
        
        Actions:
        1. Capture stack trace
        2. Emit structured log event
        3. Report to Sentry (if configured)
        4. Save HTML snapshot (if page available)
        5. Increment consecutive_failure_count
        6. Auto-disable source if 3 consecutive failures
        
        Args:
            page: Playwright page object
            source: Source model instance
            db: SQLAlchemy database session
            exception: Exception that was raised
        """
        # Capture stack trace
        stack_trace = traceback.format_exc()
        
        # Emit structured log event
        logger.error(
            "scraper.failed",
            source_id=source.id,
            source_name=source.name,
            error=str(exception),
            error_type=type(exception).__name__,
            stack_trace=stack_trace
        )
        
        # Report to Sentry (if configured)
        try:
            import sentry_sdk
            with sentry_sdk.push_scope() as scope:
                scope.set_tag("source_id", source.id)
                scope.set_tag("source_name", source.name)
                scope.set_tag("heal_mode", source.heal_mode)
                sentry_sdk.capture_exception(exception)
        except ImportError:
            # Sentry not configured
            pass
        except Exception as e:
            logger.warning(
                "scraper.sentry_report_failed",
                error=str(e)
            )
        
        # Save HTML snapshot (if page available)
        if page:
            try:
                html = await page.content()
                # Truncate to 200KB
                max_size = 200 * 1024
                if len(html) > max_size:
                    html = html[:max_size]
                
                # Save to file or database (implementation depends on requirements)
                logger.info(
                    "scraper.html_snapshot_saved",
                    source_id=source.id,
                    html_size=len(html)
                )
            except Exception as e:
                logger.warning(
                    "scraper.html_snapshot_failed",
                    error=str(e)
                )
        
        # Increment failure count
        try:
            source.consecutive_failure_count += 1
            
            logger.info(
                "scraper.failure_count_incremented",
                source_id=source.id,
                consecutive_failures=source.consecutive_failure_count
            )
            
            # Auto-disable source after 3 consecutive failures
            if source.consecutive_failure_count >= 3:
                source.is_active = False
                logger.warning(
                    "scraper.source_disabled",
                    source_id=source.id,
                    consecutive_failures=source.consecutive_failure_count
                )
            
            db.commit()
            
        except Exception as e:
            logger.warning(
                "scraper.failure_count_update_failed",
                error=str(e)
            )
