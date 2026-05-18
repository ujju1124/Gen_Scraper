"""
Google Maps Scraper Implementation

Universal background source that automatically runs for every scraping job,
providing comprehensive business data with near 100% coordinate coverage.
"""

import re
import structlog
from typing import Optional
from sqlalchemy.orm import Session

from models.source import Source
from scrapers.base_scraper import BaseScraper

logger = structlog.get_logger()


class GoogleMapsScraper(BaseScraper):
    """
    Scraper for Google Maps business listings.
    
    This is a universal source that runs automatically for all categories,
    providing enrichment data with high-quality coordinates.
    """
    
    def __init__(self):
        super().__init__()
        self.source_name = "google_maps"
    
    async def _scrape(
        self,
        page,
        source: Source,
        db: Session,
        location: str,
        max_results: Optional[int] = None,
        category_id: Optional[int] = None
    ) -> list[dict]:
        """
        Scrape business listings from Google Maps.
        
        Args:
            page: Playwright page object
            source: Source model instance
            db: SQLAlchemy database session
            location: Location string (e.g., "Kathmandu")
            max_results: Maximum results to collect (None = scrape until end)
            category_id: Job's category ID — used to look up the category name
            
        Returns:
            List of scraped business dictionaries
        """
        logger.info(
            "google_maps.scrape_start",
            location=location,
            max_results=max_results,
            category_id=category_id
        )

        # Fix 1: Get category name from the job's category_id (passed from orchestrator)
        # google_maps source has category_id=NULL (universal), so we use the job's category
        category = 'businesses'  # default
        if category_id:
            try:
                from models.category import Category
                cat = db.query(Category).filter(Category.id == category_id).first()
                if cat:
                    category = cat.name
                    logger.info("google_maps.category_resolved", category=category, category_id=category_id)
            except Exception as e:
                logger.warning("google_maps.category_lookup_failed", category_id=category_id, error=str(e))
        
        # Build search URL
        search_query = f"{category} in {location}".replace(" ", "+")
        search_url = f"https://www.google.com/maps/search/{search_query}/"
        
        logger.info(
            "google_maps.navigating",
            url=search_url,
            category=category
        )
        
        try:
            # Navigate to search page
            await page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(5000)  # Wait for Google Maps to load
            
            # Check for CAPTCHA immediately
            if await self._detect_captcha(page):
                logger.warning("google_maps.captcha_detected_early")
                return []
            
            # Collect result URLs by scrolling
            result_urls = await self._scroll_and_collect_urls(page, max_results)
            
            if not result_urls:
                logger.warning("google_maps.no_results", location=location, category=category)
                return []
            
            logger.info(
                "google_maps.urls_collected",
                count=len(result_urls),
                max_results=max_results
            )
            
            # Extract data from each detail page
            results = await self._extract_from_detail_pages(
                page,
                source,
                db,
                result_urls,
                location,
                category,
                max_results
            )
            
            logger.info(
                "google_maps.scrape_complete",
                location=location,
                category=category,
                result_count=len(results)
            )
            
            return results
            
        except Exception as e:
            logger.error(
                "google_maps.scrape_error",
                location=location,
                category=category,
                error=str(e),
                exc_info=True
            )
            await self._debug_page(page, "google_maps_error")
            return []
    
    async def _scroll_and_collect_urls(
        self,
        page,
        max_results: Optional[int]
    ) -> list[str]:
        """
        Scroll the results sidebar and collect business detail page URLs.
        
        Args:
            page: Playwright page object
            max_results: Maximum URLs to collect
            
        Returns:
            List of business detail page URLs
        """
        # Find scrollable results container
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
        max_scroll_attempts = 50  # Prevent infinite loops
        
        while scroll_attempts < max_scroll_attempts:
            # Check if we've reached max_results
            if max_results and len(result_urls) >= max_results:
                logger.info(
                    "google_maps.max_results_reached_during_scroll",
                    collected=len(result_urls),
                    max_results=max_results
                )
                break
            
            # Get current result URLs
            try:
                card_elements = await page.query_selector_all('a.hfpxzc')
                new_count = 0
                
                for card in card_elements:
                    href = await card.get_attribute('href')
                    if href and href not in seen_urls:
                        seen_urls.add(href)
                        result_urls.append(href)
                        new_count += 1
                
                logger.debug(
                    "google_maps.scroll_iteration",
                    attempt=scroll_attempts + 1,
                    new_urls=new_count,
                    total_urls=len(result_urls)
                )
                
            except Exception as e:
                logger.warning("google_maps.url_collection_error", error=str(e))
            
            # Scroll the feed container
            try:
                feed = await page.query_selector(feed_selector)
                if feed:
                    # Get current scroll height
                    current_height = await page.evaluate(
                        '(el) => el.scrollHeight',
                        feed
                    )
                    
                    # Scroll to bottom
                    await page.evaluate(
                        '(el) => el.scrollTo(0, el.scrollHeight)',
                        feed
                    )
                    
                    # Wait for new content to load
                    await page.wait_for_timeout(3000)
                    
                    # Check if we've reached the end
                    new_height = await page.evaluate(
                        '(el) => el.scrollHeight',
                        feed
                    )
                    
                    if new_height == last_height:
                        # Check for end-of-list indicator
                        end_element = await page.query_selector('.PbZDve')
                        if end_element:
                            logger.info("google_maps.end_of_list_reached")
                            break
                        
                        # Try clicking last result to trigger more loading
                        try:
                            await page.evaluate('''
                                () => {
                                    const cards = document.querySelectorAll('a.hfpxzc');
                                    if (cards.length > 0) {
                                        cards[cards.length - 1].click();
                                    }
                                }
                            ''')
                            await page.wait_for_timeout(2000)
                        except Exception:
                            pass
                    
                    last_height = new_height
                    
            except Exception as e:
                logger.warning("google_maps.scroll_error", error=str(e))
                break
            
            scroll_attempts += 1
        
        # Trim to max_results if needed
        if max_results and len(result_urls) > max_results:
            result_urls = result_urls[:max_results]
        
        return result_urls
    
    async def _extract_from_detail_pages(
        self,
        page,
        source: Source,
        db: Session,
        result_urls: list[str],
        location: str,
        category: str,
        max_results: Optional[int]
    ) -> list[dict]:
        """
        Visit each business detail page and extract data.
        
        Args:
            page: Playwright page object
            source: Source model instance
            db: SQLAlchemy database session
            result_urls: List of business detail page URLs
            location: Location string
            category: Category string
            max_results: Maximum results to extract
            
        Returns:
            List of extracted business data dictionaries
        """
        results = []
        
        for idx, url in enumerate(result_urls):
            # Check max_results limit
            if max_results and len(results) >= max_results:
                logger.info(
                    "google_maps.max_results_reached",
                    extracted=len(results),
                    max_results=max_results
                )
                break
            
            try:
                logger.debug(
                    "google_maps.extracting_detail",
                    index=idx + 1,
                    total=len(result_urls),
                    url=url
                )
                
                # Navigate to detail page
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(2000)
                
                # Check for CAPTCHA
                if await self._detect_captcha(page):
                    logger.warning(
                        "google_maps.captcha_detected",
                        results_collected=len(results)
                    )
                    # Return partial results
                    return results
                
                # Wait for main content
                try:
                    await page.wait_for_selector('[role="main"]', timeout=10000)
                except Exception:
                    logger.warning("google_maps.main_content_not_found", url=url)
                    continue
                
                # Extract business data
                business_data = await self._extract_business_data(page, source, db, url, location, category)
                
                if business_data:
                    results.append(business_data)
                    logger.debug(
                        "google_maps.business_extracted",
                        name=business_data.get('name'),
                        has_coordinates=bool(business_data.get('latitude'))
                    )
                
                # Delay between detail pages
                await page.wait_for_timeout(3000)
                
            except Exception as e:
                logger.warning(
                    "google_maps.detail_extraction_error",
                    url=url,
                    error=str(e)
                )
                continue
        
        return results
    
    async def _extract_business_data(
        self,
        page,
        source: Source,
        db: Session,
        url: str,
        location: str,
        category: str
    ) -> Optional[dict]:
        """
        Extract business data from detail page using healing-enabled extraction.
        
        Args:
            page: Playwright page object
            source: Source model instance
            db: SQLAlchemy database session
            url: Current page URL
            location: Location string
            category: Category string
            
        Returns:
            Dictionary of business data or None if extraction fails
        """
        try:
            # Wait for main content to be available
            try:
                main_elem = await page.wait_for_selector('[role="main"]', timeout=10000)
            except Exception:
                logger.warning("google_maps.main_content_not_found", url=url)
                return None
            
            # Extract name with healing
            name = await self._extract_field_with_healing(
                card=main_elem,
                page=page,
                source=source,
                db=db,
                field_name='name'
            )
            
            if not name:
                logger.warning("google_maps.name_not_found", url=url)
                return None
            
            # Extract address with healing
            address = await self._extract_field_with_healing(
                card=main_elem,
                page=page,
                source=source,
                db=db,
                field_name='address'
            )
            
            # Extract phone with healing
            phone = await self._extract_field_with_healing(
                card=main_elem,
                page=page,
                source=source,
                db=db,
                field_name='phone'
            )
            
            # Extract rating with healing
            rating_text = await self._extract_field_with_healing(
                card=main_elem,
                page=page,
                source=source,
                db=db,
                field_name='rating'
            )
            
            # Parse rating from text
            rating = None
            if rating_text:
                try:
                    rating = float(rating_text.strip())
                except (ValueError, AttributeError):
                    pass
            
            # Extract review count with healing
            review_text = await self._extract_field_with_healing(
                card=main_elem,
                page=page,
                source=source,
                db=db,
                field_name='review_count'
            )
            
            # Parse review count from text
            review_count = None
            if review_text:
                match = re.search(r'([\d,]+)', review_text)
                if match:
                    review_count_str = match.group(1).replace(',', '')
                    try:
                        review_count = int(review_count_str)
                    except ValueError:
                        pass
            
            # Extract website - special handling for href attribute
            website = None
            website_selector_record = self.selectors.get('website')
            if website_selector_record:
                try:
                    website_link = await main_elem.query_selector(website_selector_record.selector)
                    if website_link:
                        website = await website_link.get_attribute('href')
                except Exception:
                    pass
            
            # Extract category label with healing
            category_label = await self._extract_field_with_healing(
                card=main_elem,
                page=page,
                source=source,
                db=db,
                field_name='category_label'
            )
            
            # Extract business status with healing
            business_status = await self._extract_field_with_healing(
                card=main_elem,
                page=page,
                source=source,
                db=db,
                field_name='business_status'
            )
            
            # Extract thumbnail_url (business photo)
            thumbnail_url = None
            try:
                thumbnail_url = await page.evaluate('''() => {
                    const img = document.querySelector('button[jsaction*="photo"] img, .RZ66Rb.FgCUCc img, [data-photo-index] img');
                    return img ? img.src : null;
                }''')
            except Exception as e:
                logger.debug("google_maps.thumbnail_extraction_failed", error=str(e))
            
            # Extract coordinates from URL
            latitude, longitude = self._parse_coordinates_from_url(url)
            
            # Build result dictionary
            result = {
                "name": name,
                "address": address,  # Leave None if not found
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
                "currency": "NPR",  # Default for Nepal
            }
            
            return result
            
        except Exception as e:
            logger.error(
                "google_maps.extraction_error",
                url=url,
                error=str(e)
            )
            return None
    
    def _parse_coordinates_from_url(self, url: str) -> tuple[Optional[float], Optional[float]]:
        """
        Parse latitude and longitude from Google Maps URL.
        
        Google Maps URLs contain coordinates in multiple formats:
        - .../@27.6826021,85.3323243,...
        - ...!3d27.6826021!4d85.3323243...
        
        Args:
            url: Google Maps URL
            
        Returns:
            Tuple of (latitude, longitude) or (None, None) if parsing fails
        """
        try:
            # Try pattern 1: !3dLAT!4dLNG (most common in detail pages)
            match = re.search(r'!3d(-?\d+\.?\d*)!4d(-?\d+\.?\d*)', url)
            if match:
                latitude = float(match.group(1))
                longitude = float(match.group(2))
                
                logger.debug(
                    "google_maps.coordinates_parsed",
                    latitude=latitude,
                    longitude=longitude,
                    pattern="3d4d"
                )
                
                return latitude, longitude
            
            # Try pattern 2: @LAT,LNG (fallback)
            match = re.search(r'@(-?\d+\.\d+),(-?\d+\.\d+)', url)
            if match:
                latitude = float(match.group(1))
                longitude = float(match.group(2))
                
                logger.debug(
                    "google_maps.coordinates_parsed",
                    latitude=latitude,
                    longitude=longitude,
                    pattern="@"
                )
                
                return latitude, longitude
            
            logger.warning("google_maps.coordinates_not_found_in_url", url=url)
            return None, None
                
        except Exception as e:
            logger.warning(
                "google_maps.coordinate_parsing_error",
                url=url,
                error=str(e)
            )
            return None, None
