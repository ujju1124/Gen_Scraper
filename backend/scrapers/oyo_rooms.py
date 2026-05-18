"""
OYO Rooms scraper implementation.

Scrapes hotel listings from OYO Rooms Nepal.
"""
import structlog
import re
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from models.source import Source
from scrapers.base_scraper import BaseScraper

logger = structlog.get_logger()


class OYORoomsScraper(BaseScraper):
    """
    Scraper for OYO Rooms hotel listings in Nepal.
    """
    
    def __init__(self):
        super().__init__()
        self.source_name = "oyo_rooms"
        self.base_url = "https://www.oyorooms.com"
    
    async def _scrape(self, page, source: Source, db: Session, location: str, max_results: Optional[int] = None, category_id: Optional[int] = None) -> list[dict]:
        """
        Scrape hotel listings from OYO Rooms.
        
        Args:
            page: Playwright page object
            source: Source model instance
            db: SQLAlchemy database session
            location: Location string (e.g., "Kathmandu")
            
        Returns:
            List of scraped hotel dictionaries
        """
        logger.info("oyo_rooms.scrape_start", location=location)
        
        # Build search URL
        search_url = self._build_search_url(location)
        
        try:
            # Navigate to search page
            await page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
            
            # Handle cookie consent
            try:
                await page.click('button:has-text("Accept"), button:has-text("Agree")', timeout=5000)
            except Exception:
                pass
            
            # Wait for hotel cards - try multiple selectors
            try:
                await page.wait_for_selector(
                    '[data-testid="hotel-card"], .hotelCardWrapper, div[class*="HotelCard"], div[class*="hotel-card"]',
                    timeout=20000
                )
            except Exception as e:
                logger.warning("oyo_rooms.no_cards_found", error=str(e))
                await self._debug_page(page, "oyo_no_cards")
                return []
            
            hotels = []
            page_num = 1
            max_pages = 5
            
            while page_num <= max_pages:
                logger.info("oyo_rooms.scraping_page", page=page_num, location=location)
                
                # Extract hotels from current page
                page_hotels = await self._extract_hotels_from_page(page, source, db, location)
                
                if not page_hotels:
                    logger.info("oyo_rooms.no_hotels_found", page=page_num)
                    break
                
                hotels.extend(page_hotels)
                logger.info("oyo_rooms.page_scraped", page=page_num, count=len(page_hotels))
                
                # Check for next page
                has_next = await self._has_next_page(page)
                if not has_next:
                    logger.info("oyo_rooms.last_page_reached", page=page_num)
                    break
                
                # Click next page
                await self._click_next_page(page)
                await page.wait_for_timeout(3000)
                page_num += 1
            
            logger.info("oyo_rooms.scrape_complete", location=location, total=len(hotels))
            return hotels
            
        except Exception as e:
            logger.error("oyo_rooms.scrape_error", location=location, error=str(e))
            await self._debug_page(page, "oyo_error")
            return []
    
    async def _extract_hotels_from_page(self, page, source: Source, db: Session, location: str) -> List[Dict[str, Any]]:
        """Extract hotel data from the current page using healing-enabled extraction."""
        hotels = []
        
        # Use locator API with multiple possible selectors
        cards = page.locator('[data-testid="hotel-card"], .hotelCardWrapper, div[class*="HotelCard"], div[class*="hotel-card"]')
        count = await cards.count()
        logger.info("oyo_rooms.cards_found", count=count)
        
        for i in range(count):
            card = cards.nth(i)
            try:
                # Convert Playwright Locator to ElementHandle for healing
                card_element = await card.element_handle()
                if not card_element:
                    continue
                
                # Extract name with healing
                name = await self._extract_field_with_healing(
                    card=card_element,
                    page=page,
                    source=source,
                    db=db,
                    field_name='name'
                )
                
                if not name:
                    continue
                
                # Extract address with healing
                address = await self._extract_field_with_healing(
                    card=card_element,
                    page=page,
                    source=source,
                    db=db,
                    field_name='address'
                )
                
                # Extract price with healing
                price_text = await self._extract_field_with_healing(
                    card=card_element,
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
                    card=card_element,
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
                        rating_val = float(rating_match.group(1))
                        if 0 <= rating_val <= 5:
                            rating_overall = rating_val
                
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
                logger.warning("oyo_rooms.extract_hotel_error", card_index=i, error=str(e))
                continue
        
        return hotels
    
    async def _has_next_page(self, page) -> bool:
        """Check if there's a visible, enabled next page button or Load More."""
        try:
            next_button = await page.query_selector('button:has-text("Next"), button:has-text("Load More"), a:has-text("Next")')
            if not next_button:
                return False
            is_disabled = await next_button.get_attribute('disabled')
            if is_disabled is not None:
                return False
            return await next_button.is_visible()
        except Exception:
            return False

    async def _click_next_page(self, page):
        """Click the next page or Load More button with a short timeout."""
        try:
            next_button = await page.query_selector('button:has-text("Next"), button:has-text("Load More"), a:has-text("Next")')
            if next_button:
                await next_button.click(timeout=5000)
                await page.wait_for_timeout(2000)
        except Exception as e:
            logger.warning("oyo_rooms.click_next_error", error=str(e))
    
    def _build_search_url(self, location: str) -> str:
        """
        Build OYO Rooms search URL for the given location.
        
        Args:
            location: City name
            
        Returns:
            Full search URL
        """
        # Calculate checkin/checkout dates (tomorrow and day after)
        checkin = datetime.now() + timedelta(days=1)
        checkout = checkin + timedelta(days=1)
        
        # Format dates as DD/MM/YYYY
        checkin_str = checkin.strftime('%d/%m/%Y')
        checkout_str = checkout.strftime('%d/%m/%Y')
        
        # OYO Rooms search URL pattern
        url = (
            f"{self.base_url}/search/?"
            f"location={location}%2C+Bagmati%2C+Nepal&"
            f"city={location}&"
            f"searchType=city&"
            f"checkin={checkin_str}&"
            f"checkout={checkout_str}&"
            f"roomConfig%5B%5D=1&"
            f"country=nepal&"
            f"guests=1&"
            f"rooms=1"
        )
        
        return url
