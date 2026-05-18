"""
Foodmandu Scraper — Phase 7 Priority 5

This scraper targets Foodmandu.com for restaurant listings in Nepal.
URL: https://foodmandu.com/Restaurant
Technology: AsyncCamoufox (Angular SPA - dynamic content)
Pagination: Infinite scroll (scroll to bottom, wait, load more)

IMPORTANT: Foodmandu is a fully dynamic Angular SPA with {{vendor.Name}} template tags.
httpx/BeautifulSoup will only return empty templates. Playwright is mandatory.
"""

import structlog
from typing import Optional
from sqlalchemy.orm import Session

from scrapers.base_scraper import BaseScraper
from models.source import Source

logger = structlog.get_logger()


class FoodmanduScraper(BaseScraper):
    """
    Scraper for Foodmandu.com restaurant listings.
    
    Target URL: https://foodmandu.com/Restaurant
    Technology: AsyncCamoufox (Playwright-based) - Angular SPA requires JavaScript execution
    Pagination: Infinite scroll - scroll to bottom, wait 2 seconds, check for new cards
    Location: Kathmandu only (Foodmandu operates only in Kathmandu)
    """
    
    def __init__(self):
        super().__init__()
        self.source_name = "foodmandu"
    
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
        Scrape restaurant listings from Foodmandu using infinite scroll.
        
        Args:
            page: Playwright page object
            source: Source model instance
            db: SQLAlchemy database session
            location: City name (ignored - Foodmandu only operates in Kathmandu)
            max_results: Maximum number of results to collect (None = unlimited)
            
        Returns:
            List of scraped restaurant dictionaries
        """
        
        results = []
        url = "https://foodmandu.com/Restaurant"
        
        logger.info(
            "scraper.started",
            source_name=self.source_name,
            url=url,
            max_results=max_results
        )
        
        try:
            # Navigate to page
            await page.goto(url, wait_until="networkidle", timeout=30000)
            
            # CRITICAL: Wait for Angular to render content
            logger.info("scraper.waiting_for_angular", source_name=self.source_name)
            await page.wait_for_timeout(5000)  # 5 second wait for Angular
            
            # Wait for restaurant cards to appear
            try:
                await page.wait_for_selector("div.listing", timeout=10000)
            except Exception as e:
                logger.error(
                    "scraper.no_cards_loaded",
                    source_name=self.source_name,
                    error=str(e)
                )
                return []
            
            # Check for CAPTCHA
            if await self._detect_captcha(page):
                logger.error(
                    "scraper.captcha_detected",
                    source_name=self.source_name
                )
                return []
            
            # Infinite scroll pagination
            scroll_attempts = 0
            max_scroll_attempts = 20  # Prevent infinite loops
            no_new_cards_count = 0
            
            while scroll_attempts < max_scroll_attempts:
                # Get current card count
                cards_before = await page.query_selector_all("div.listing")
                current_count = len(cards_before)
                
                logger.info(
                    "scraper.scroll_attempt",
                    source_name=self.source_name,
                    scroll_attempt=scroll_attempts + 1,
                    current_cards=current_count,
                    extracted_results=len(results)
                )
                
                # Extract data from new cards (only process cards we haven't seen yet)
                cards = await page.query_selector_all("div.listing")
                
                for i in range(len(results), len(cards)):
                    # Check max_results limit before processing
                    if max_results and len(results) >= max_results:
                        logger.info(
                            "scraper.max_results_reached",
                            source_name=self.source_name,
                            result_count=len(results)
                        )
                        return results
                    
                    try:
                        card = cards[i]
                        
                        # Extract name with healing
                        name = await self._extract_field_with_healing(
                            card=card,
                            page=page,
                            source=source,
                            db=db,
                            field_name='name'
                        )
                        
                        if not name:
                            continue
                        
                        # Extract address with healing
                        address = await self._extract_field_with_healing(
                            card=card,
                            page=page,
                            source=source,
                            db=db,
                            field_name='address'
                        )
                        
                        # Extract cuisine with healing
                        cuisine_text = await self._extract_field_with_healing(
                            card=card,
                            page=page,
                            source=source,
                            db=db,
                            field_name='cuisine'
                        )
                        
                        # Parse cuisine into amenities
                        amenities = None
                        if cuisine_text:
                            amenities = [c.strip() for c in cuisine_text.split('|')]
                        
                        # Extract thumbnail - special handling for img src
                        thumbnail_url = None
                        thumbnail_selector_record = self.selectors.get('thumbnail')
                        if thumbnail_selector_record:
                            try:
                                img_elem = await card.query_selector(thumbnail_selector_record.selector)
                                if img_elem:
                                    img_src = await img_elem.get_attribute('src')
                                    if img_src and not img_src.endswith('no-image.jpg'):
                                        thumbnail_url = img_src
                            except Exception:
                                pass
                        
                        # Extract detail link - special handling for href
                        url = None
                        try:
                            link_elem = await card.query_selector("div.title20 a")
                            if link_elem:
                                href = await link_elem.get_attribute('href')
                                if href:
                                    if href.startswith('/'):
                                        url = f"https://foodmandu.com{href}"
                                    else:
                                        url = href
                        except Exception:
                            pass
                        
                        result = {
                            'name': name,
                            'address': address,
                            'amenities': amenities,
                            'thumbnail_url': thumbnail_url,
                            'url': url,
                            'city': "Kathmandu",  # Foodmandu only operates in Kathmandu
                            'country': 'Nepal'
                        }
                        
                        results.append(result)
                        logger.debug(
                            "scraper.card_extracted",
                            source_name=self.source_name,
                            name=result['name'],
                            total_results=len(results)
                        )
                    
                    except Exception as e:
                        logger.warning(
                            "scraper.card_extraction_failed",
                            source_name=self.source_name,
                            card_index=i,
                            error=str(e)
                        )
                        continue
                
                # Scroll to bottom to trigger loading more restaurants
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                
                # Wait for new content to load
                await page.wait_for_timeout(2000)
                
                # Check if new cards loaded
                cards_after = await page.query_selector_all("div.listing")
                new_count = len(cards_after)
                
                if new_count == current_count:
                    no_new_cards_count += 1
                    logger.info(
                        "scraper.no_new_cards",
                        source_name=self.source_name,
                        consecutive_attempts=no_new_cards_count
                    )
                    
                    # If no new cards after 2 consecutive attempts, we've reached the end
                    if no_new_cards_count >= 2:
                        logger.info(
                            "scraper.end_of_results",
                            source_name=self.source_name,
                            final_count=len(results)
                        )
                        break
                else:
                    no_new_cards_count = 0  # Reset counter
                
                scroll_attempts += 1
            
            logger.info(
                "scraper.completed",
                source_name=self.source_name,
                total_results=len(results),
                scroll_attempts=scroll_attempts
            )
            
            return results
        
        except Exception as e:
            logger.error(
                "scraper.failed",
                source_name=self.source_name,
                error=str(e),
                error_type=type(e).__name__
            )
            return results  # Return whatever we collected before the error
