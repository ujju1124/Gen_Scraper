"""
eSewa Hotels scraper implementation.

Scrapes hotel listings from eSewa Hotels (esewahotels.com).
"""
import structlog
import re
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from models.source import Source
from scrapers.base_scraper import BaseScraper

logger = structlog.get_logger()


class ESewaHotelsScraper(BaseScraper):
    """
    Scraper for eSewa Hotels listings.
    """

    def __init__(self):
        super().__init__()
        self.source_name = "esewa_hotels"
        self.base_url = "https://esewahotels.com"

    async def _scrape(self, page, source: Source, db: Session, location: str, max_results: Optional[int] = None, category_id: Optional[int] = None) -> list[dict]:
        """
        Scrape hotel listings from eSewa Hotels.

        Args:
            page: Playwright page object
            source: Source model instance
            db: SQLAlchemy database session
            location: Location string (e.g., "Kathmandu")
            max_results: Maximum results to collect (None = scrape all 45 pages)

        Returns:
            List of scraped hotel dictionaries
        """
        logger.info("esewa_hotels.scrape_start", location=location, max_results=max_results)

        search_url = self._build_search_url(location)

        try:
            await page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
            
            # Check if a search button needs to be clicked
            try:
                search_btn = await page.query_selector('button[type="submit"], input[type="submit"]', timeout=3000)
                if search_btn:
                    await search_btn.click()
                    await page.wait_for_timeout(2000)
            except Exception:
                pass
            
            # Wait for hotel listings to appear
            # eSewa Hotels shows hotel links as a[href*="/hotel/"]
            try:
                await page.wait_for_selector(
                    'a[href*="/hotel/"]',
                    timeout=15000
                )
            except Exception as e:
                logger.warning("esewa_hotels.no_listings_found", error=str(e))
                await self._debug_page(page, "esewa_no_listings")
                return []

            hotels = []
            page_num = 1
            max_pages = 50  # eSewa Hotels has ~45 pages for Kathmandu (221 properties, 5/page)

            while page_num <= max_pages:
                try:
                    logger.info(
                        "esewa_hotels.scraping_page",
                        page=page_num,
                        url=page.url,
                        collected=len(hotels),
                        max_results=max_results
                    )

                    # Wait for hotel links to be present
                    await page.wait_for_selector('a[href*="/hotel/"]', timeout=15000)
                    await page.wait_for_timeout(500)

                    # Extract hotel data from current page
                    page_hotels = await self._extract_hotels_from_page(page, source, db, location)
                    
                    # Add new hotels, stopping exactly at max_results
                    for hotel in page_hotels:
                        hotels.append(hotel)
                        if max_results and len(hotels) >= max_results:
                            logger.info(
                                "esewa_hotels.max_results_reached",
                                page=page_num,
                                count=len(hotels),
                                max_results=max_results
                            )
                            logger.info("esewa_hotels.scrape_complete", location=location, total=len(hotels))
                            return hotels[:max_results]

                    logger.info(
                        "esewa_hotels.page_extracted",
                        page=page_num,
                        hotels_on_page=len(page_hotels),
                        total_hotels=len(hotels)
                    )

                    # eSewa Hotels pagination:
                    # - Uses nav[aria-label="Page navigation example"]
                    # - "Next" link present on all pages except the last
                    # - URL pattern: ?...&page=N
                    next_href = await page.evaluate("""
                        () => {
                            const nav = document.querySelector('nav[aria-label*="Page"]');
                            if (!nav) return null;
                            const links = Array.from(nav.querySelectorAll('a'));
                            const nextLink = links.find(a => a.textContent.trim() === 'Next');
                            return nextLink ? nextLink.href : null;
                        }
                    """)

                    if not next_href:
                        logger.info(
                            "esewa_hotels.no_next_page",
                            page=page_num,
                            total_hotels=len(hotels)
                        )
                        break

                    # Navigate directly to next page URL
                    await page.goto(next_href, wait_until="domcontentloaded", timeout=30000)
                    page_num += 1

                except Exception as e:
                    logger.error(
                        "esewa_hotels.page_error",
                        page=page_num,
                        error=str(e)
                    )
                    break

            logger.info("esewa_hotels.scrape_complete", location=location, total=len(hotels))
            return hotels

        except Exception as e:
            logger.error("esewa_hotels.scrape_error", location=location, error=str(e))
            await self._debug_page(page, "esewa_error")
            return []

    async def _extract_hotels_from_page(self, page, source: Source, db: Session, location: str) -> List[Dict[str, Any]]:
        """Extract hotel data from the current page using healing-enabled extraction."""
        hotels = []

        # Find all hotel links - try multiple patterns
        hotel_links = await page.query_selector_all('a[href*="/hotel/"], a[href*="/hotels/"], .hotel-item a, .property-card a')
        logger.info("esewa_hotels.links_found", count=len(hotel_links))

        for link in hotel_links:
            try:
                # Extract name with healing
                name = await self._extract_field_with_healing(
                    card=link,
                    page=page,
                    source=source,
                    db=db,
                    field_name='name'
                )
                
                if not name or len(name) < 3:
                    continue

                # Extract price with healing
                price_text = await self._extract_field_with_healing(
                    card=link,
                    page=page,
                    source=source,
                    db=db,
                    field_name='price'
                )
                
                # Parse price from text
                price_min = None
                if price_text:
                    price_match = re.search(r'([\d,\.]+)', price_text)
                    if price_match:
                        price_min = float(price_match.group(1).replace(',', ''))

                # Extract rating with healing
                rating_text = await self._extract_field_with_healing(
                    card=link,
                    page=page,
                    source=source,
                    db=db,
                    field_name='rating'
                )
                
                # Parse rating from text
                rating_overall = None
                if rating_text:
                    rating_match = re.search(r'(\d+\.?\d*)', rating_text)
                    if rating_match:
                        rating_overall = float(rating_match.group(1))

                hotel_data = {
                    "name": name,
                    "address": f"{name}, {location}",
                    "city": location,
                    "price_min": price_min,
                    "rating_overall": rating_overall,
                    "currency": "NPR",
                }

                hotels.append(hotel_data)

            except Exception as e:
                logger.warning("esewa_hotels.extract_hotel_error", error=str(e))
                continue

        return hotels

    async def _has_next_page(self, page) -> bool:
        """Check if there's a visible next page link."""
        try:
            next_link = await page.query_selector('a[href*="page="]')
            if not next_link:
                return False
            return await next_link.is_visible()
        except Exception:
            return False

    async def _click_next_page(self, page):
        """Click the next page link with a short timeout."""
        try:
            next_link = await page.query_selector('a:has-text("Next"), a[href*="page="]')
            if next_link:
                await next_link.click(timeout=5000)
                await page.wait_for_timeout(3000)
        except Exception as e:
            logger.warning("esewa_hotels.click_next_error", error=str(e))

    def _build_search_url(self, location: str) -> str:
        """Build eSewa Hotels search URL for the given location."""
        checkin = datetime.now() + timedelta(days=1)
        checkout = checkin + timedelta(days=1)
        
        # Use lowercase location for URL path, capitalized for dest parameter
        location_lower = location.lower()
        location_title = location.title()

        url = (
            f"{self.base_url}/searchresults/{location_lower}?"
            f"dest={location_title}&"
            f"dest_type=city&"
            f"checkin={checkin.strftime('%Y-%m-%d')}&"
            f"checkout={checkout.strftime('%Y-%m-%d')}&"
            f"adults=1&children=0&rooms=1&nationality=np"
        )

        return url
