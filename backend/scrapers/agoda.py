"""
Agoda scraper implementation.

Scrapes hotel listings from Agoda.
"""
import structlog
import re
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from models.source import Source
from scrapers.base_scraper import BaseScraper

logger = structlog.get_logger()


class AgodaScraper(BaseScraper):
    """
    Scraper for Agoda hotel listings.
    
    Uses Camoufox browser for anti-detection.
    """
    
    def __init__(self):
        super().__init__()
        self.source_name = "agoda"
        self.base_url = "https://www.agoda.com"
    
    async def _scrape(self, page, source: Source, db: Session, location: str, max_results: Optional[int] = None, category_id: Optional[int] = None) -> list[dict]:
        """
        Scrape hotel listings from Agoda.
        
        Args:
            page: Playwright page object
            source: Source model instance
            db: SQLAlchemy database session
            location: Location string (e.g., "Kathmandu")
            
        Returns:
            List of scraped hotel dictionaries
        """
        logger.info("agoda.scrape_start", location=location)
        
        # Build search URL
        search_url = self._build_search_url(location)
        
        try:
            # Navigate to search page
            await page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
            
            # Handle cookie consent if present
            try:
                await page.click('button:has-text("Accept"), button:has-text("Agree"), button:has-text("OK")', timeout=5000)
                logger.info("agoda.cookie_accepted")
            except Exception:
                pass
            
            # Wait for hotel cards to load - try multiple possible selectors
            try:
                await page.wait_for_selector(
                    '[data-element-name="property-card"], [data-selenium="hotel-item"], .PropertyCard, [class*="PropertyCard"]',
                    timeout=20000
                )
            except Exception as e:
                logger.warning("agoda.no_cards_found", error=str(e))
                await self._debug_page(page, "agoda_no_cards")
                return []
            
            hotels = []
            page_num = 1
            max_pages = 5
            
            while page_num <= max_pages:
                logger.info("agoda.scraping_page", page=page_num, location=location)
                
                # Extract hotels from current page
                page_hotels = await self._extract_hotels_from_page(page, source.id, location)
                
                if not page_hotels:
                    logger.info("agoda.no_hotels_found", page=page_num)
                    break
                
                hotels.extend(page_hotels)
                logger.info("agoda.page_scraped", page=page_num, count=len(page_hotels))
                
                # Check for next page
                has_next = await self._has_next_page(page)
                if not has_next:
                    logger.info("agoda.last_page_reached", page=page_num)
                    break
                
                # Click next page
                await self._click_next_page(page)
                await page.wait_for_timeout(4000)
                page_num += 1
            
            logger.info("agoda.scrape_complete", location=location, total=len(hotels))
            return hotels
            
        except Exception as e:
            logger.error("agoda.scrape_error", location=location, error=str(e))
            await self._debug_page(page, "agoda_error")
            return []
    
    async def _extract_hotels_from_page(self, page, source_id: int, location: str) -> List[Dict[str, Any]]:
        """Extract hotel data from the current page using robust selectors."""
        hotels = []
        
        # Use locator API (more robust) - try multiple possible selectors
        cards = page.locator('[data-element-name="property-card"], [data-selenium="hotel-item"], .PropertyCard, [class*="PropertyCard"]')
        card_count = await cards.count()
        logger.info("agoda.cards_found", count=card_count)
        
        for i in range(card_count):
            card = cards.nth(i)
            try:
                # Extract hotel name - try multiple selectors
                try:
                    name_elem = card.locator('h3, [data-element-name="property-name"], [class*="PropertyName"]').first
                    name = await name_elem.text_content(timeout=2000)
                    name = name.strip() if name else None
                except Exception:
                    name = None
                
                if not name:
                    continue
                
                # Extract address - optional
                address = None
                try:
                    addr_elem = card.locator('[class*="address"], [class*="location"], p').first
                    address = await addr_elem.text_content(timeout=1000)
                    address = address.strip() if address else None
                except Exception:
                    pass
                
                # Extract price - look for text containing NPR or numbers
                price_min = None
                try:
                    price_elem = card.locator('[class*="Price"], [class*="price"], text=/NPR|Rs\\.?\\s*[\\d,]+/').first
                    price_text = await price_elem.text_content(timeout=1000)
                    price_match = re.search(r'([\d,\.]+)', price_text)
                    if price_match:
                        price_min = float(price_match.group(1).replace(',', ''))
                except Exception:
                    pass
                
                # Extract rating
                rating_overall = None
                try:
                    rating_elem = card.locator('[class*="Review"], [class*="rating"], [class*="Rating"]').first
                    rating_text = await rating_elem.text_content(timeout=1000)
                    rating_match = re.search(r'(\d+\.?\d*)', rating_text)
                    if rating_match:
                        rating_val = float(rating_match.group(1))
                        if 0 <= rating_val <= 10:  # Agoda uses 0-10 scale
                            rating_overall = rating_val
                except Exception:
                    pass
                
                hotel_data = {
                    "name": name,
                    "address": address or f"{name}, {location}",
                    "city": location,
                    "price_min": price_min,
                    "rating_overall": rating_overall,
                    "currency": "NPR"
                }
                
                hotels.append(hotel_data)
                
            except Exception as e:
                logger.warning("agoda.extract_hotel_error", card_index=i, error=str(e))
                continue
        
        return hotels
    
    async def _has_next_page(self, page) -> bool:
        """Check if there's a visible, enabled next page button."""
        try:
            next_button = await page.query_selector('button[aria-label*="Next"], button[class*="next"]')
            if not next_button:
                return False
            is_disabled = await next_button.get_attribute('disabled')
            if is_disabled is not None:
                return False
            return await next_button.is_visible()
        except Exception:
            return False

    async def _click_next_page(self, page):
        """Click the next page button with a short timeout."""
        try:
            next_button = await page.query_selector('button[aria-label*="Next"], button[class*="next"]')
            if next_button:
                await next_button.click(timeout=5000)
                await page.wait_for_timeout(4000)
        except Exception as e:
            logger.warning("agoda.click_next_error", error=str(e))
    
    def _build_search_url(self, location: str) -> str:
        """
        Build Agoda search URL for the given location.
        
        Args:
            location: City name
            
        Returns:
            Full search URL
        """
        # Calculate checkin/checkout dates (tomorrow and day after)
        checkin = datetime.now() + timedelta(days=1)
        checkout = checkin + timedelta(days=1)
        
        # Agoda search URL pattern
        url = (
            f"{self.base_url}/search?"
            f"city={location}&"
            f"checkIn={checkin.strftime('%Y-%m-%d')}&"
            f"checkOut={checkout.strftime('%Y-%m-%d')}&"
            f"rooms=1&adults=1&children=0"
        )
        
        return url
