"""
Hostelworld Scraper Stub

This scraper targets Hostelworld.com for hostel and budget accommodation listings in Nepal.
URL pattern: https://www.hostelworld.com/hostels/asia/nepal/{city}/
Pagination: Page-based (?page=N)
"""

import structlog
from typing import Optional
from sqlalchemy.orm import Session

from scrapers.base_scraper import BaseScraper
from models.source import Source

logger = structlog.get_logger()


class HostelworldScraper(BaseScraper):
    """
    Scraper for Hostelworld.com hostel listings.
    
    Target URL: https://www.hostelworld.com/hostels/asia/nepal/{city}/
    Pagination: ?page=1, ?page=2, etc.
    Browser: AsyncCamoufox (Playwright-based)
    """
    
    def __init__(self):
        super().__init__()
        self.source_name = "hostelworld"
    
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
        Scrape hostel listings from Hostelworld.
        
        Args:
            page: Playwright page object
            source: Source model instance
            db: SQLAlchemy database session
            location: City name (e.g., "Kathmandu", "Pokhara")
            max_results: Maximum number of results to collect (None = unlimited)
            
        Returns:
            List of scraped hostel dictionaries
        """
        import re
        
        results = []
        page_num = 1
        
        # Build base URL
        base_url = f"https://www.hostelworld.com/hostels/asia/nepal/{location.lower()}/"
        
        logger.info(
            "scraper.started",
            source_name=self.source_name,
            location=location,
            max_results=max_results
        )
        
        while True:
            # Build paginated URL
            if page_num == 1:
                url = base_url
            else:
                url = f"{base_url}?page={page_num}"
            
            logger.info(
                "scraper.page_started",
                source_name=self.source_name,
                page_num=page_num,
                url=url
            )
            
            try:
                # Navigate to page
                await page.goto(url, wait_until="networkidle", timeout=30000)
                await page.wait_for_timeout(3000)  # Wait for dynamic content
                
                # Check for CAPTCHA
                if await self._detect_captcha(page):
                    logger.error(
                        "scraper.captcha_detected",
                        source_name=self.source_name,
                        page_num=page_num
                    )
                    break
                
                # Get card container selector
                card_selector = self.selectors.get('card_container')
                if not card_selector:
                    logger.error(
                        "scraper.selector_missing",
                        field_name="card_container"
                    )
                    break
                
                # Find all hostel cards
                cards = await page.query_selector_all(card_selector.selector)
                
                if not cards:
                    logger.info(
                        "scraper.no_results",
                        source_name=self.source_name,
                        page_num=page_num
                    )
                    break
                
                logger.info(
                    "scraper.cards_found",
                    source_name=self.source_name,
                    page_num=page_num,
                    card_count=len(cards)
                )
                
                # Extract data from each card
                for idx, card in enumerate(cards):
                    try:
                        result = {}
                        
                        # Extract detail link first (the card itself is a link)
                        detail_url = await card.get_attribute('href')
                        if detail_url:
                            if detail_url.startswith('/'):
                                result['url'] = f"https://www.hostelworld.com{detail_url}"
                            else:
                                result['url'] = detail_url
                        
                        # Get inner text of the entire card for parsing
                        card_text = await card.inner_text()
                        
                        # Extract name from card text (first substantial line)
                        # Hostelworld structure: name is first line, not in a specific heading tag
                        lines = [line.strip() for line in card_text.split('\n') if line.strip()]
                        if lines:
                            # First line is the hostel name
                            result['name'] = lines[0]
                        
                        # Extract rating and review count from text
                        # Pattern: "9.4 Superb (169)" or "10 Superb (20)"
                        if 'rating_text' in self.selectors:
                            rating_match = re.search(r'(\d+\.?\d*)\s+(Superb|Excellent|Very Good|Good|Fair|Poor)\s+\((\d+)\)', card_text)
                            if rating_match:
                                result['rating_overall'] = float(rating_match.group(1))
                                result['rating_label'] = rating_match.group(2)
                                result['review_count'] = int(rating_match.group(3))
                        
                        # Extract distance from city centre
                        # Pattern: "1.22km from city centre"
                        if 'distance' in self.selectors:
                            distance_match = re.search(r'([\d.]+)km from city centre', card_text)
                            if distance_match:
                                result['distance_from_centre'] = float(distance_match.group(1))
                        
                        # Extract prices
                        # Pattern: "Privates From NPR1615.22" or "Dorms From NPR1094.53"
                        if 'price_text' in self.selectors:
                            # Extract dorm price
                            dorm_match = re.search(r'Dorms From\s+NPR\s*([\d,]+\.?\d*)', card_text)
                            if dorm_match:
                                price_str = dorm_match.group(1).replace(',', '')
                                result['price_min'] = float(price_str)
                                result['price_range_label'] = 'Dorm Bed'
                            
                            # Extract private room price
                            private_match = re.search(r'Privates From\s+NPR\s*([\d,]+\.?\d*)', card_text)
                            if private_match:
                                price_str = private_match.group(1).replace(',', '')
                                # If no dorm price, use private as min
                                if 'price_min' not in result:
                                    result['price_min'] = float(price_str)
                                    result['price_range_label'] = 'Private Room'
                                else:
                                    result['price_max'] = float(price_str)
                        
                        # Extract description (remaining text after removing structured data)
                        if 'description' in self.selectors:
                            desc_elem = await card.query_selector(self.selectors['description'].selector)
                            if desc_elem:
                                desc_text = (await desc_elem.inner_text()).strip()
                                # Only use if it's substantial (more than 20 chars)
                                if len(desc_text) > 20:
                                    result['description_short'] = desc_text[:500]  # Limit to 500 chars
                        
                        # Extract thumbnail image
                        if 'thumbnail' in self.selectors:
                            img_elem = await card.query_selector(self.selectors['thumbnail'].selector)
                            if img_elem:
                                img_src = await img_elem.get_attribute('src')
                                if img_src:
                                    result['thumbnail_url'] = img_src
                        
                        # Add metadata
                        result['city'] = location
                        result['country'] = 'Nepal'
                        result['property_type'] = 'Hostel'
                        result['currency'] = 'NPR'
                        
                        # Only add if we got at least a name
                        if result.get('name'):
                            results.append(result)
                            
                            logger.debug(
                                "scraper.hostel_extracted",
                                source_name=self.source_name,
                                hostel_name=result.get('name'),
                                price=result.get('price_min'),
                                rating=result.get('rating_overall')
                            )
                            
                            # Check max_results limit
                            if max_results and len(results) >= max_results:
                                logger.info(
                                    "scraper.max_results_reached",
                                    source_name=self.source_name,
                                    result_count=len(results)
                                )
                                return results
                        else:
                            logger.warning(
                                "scraper.no_name_found",
                                source_name=self.source_name,
                                card_index=idx,
                                card_text_preview=card_text[:100]
                            )
                    
                    except Exception as e:
                        logger.warning(
                            "scraper.card_extraction_failed",
                            source_name=self.source_name,
                            card_index=idx,
                            error=str(e)
                        )
                        continue
                
                logger.info(
                    "scraper.page_completed",
                    source_name=self.source_name,
                    page_num=page_num,
                    cards_found=len(cards),
                    total_results=len(results)
                )
                
                # Check for next page
                if 'pagination_next' in self.selectors:
                    # Look for pagination links
                    next_links = await page.query_selector_all(self.selectors['pagination_next'].selector)
                    
                    # Check if there's a link for the next page number
                    has_next_page = False
                    for link in next_links:
                        href = await link.get_attribute('href')
                        if href and f'page={page_num + 1}' in href:
                            has_next_page = True
                            break
                    
                    if not has_next_page:
                        logger.info(
                            "scraper.no_more_pages",
                            source_name=self.source_name,
                            final_page=page_num
                        )
                        break
                else:
                    # No pagination selector configured, assume single page
                    logger.info(
                        "scraper.single_page_mode",
                        source_name=self.source_name
                    )
                    break
                
                page_num += 1
                
                # Safety limit: max 10 pages
                if page_num > 10:
                    logger.warning(
                        "scraper.page_limit_reached",
                        source_name=self.source_name,
                        max_pages=10
                    )
                    break
            
            except Exception as e:
                logger.error(
                    "scraper.page_error",
                    source_name=self.source_name,
                    page_num=page_num,
                    error=str(e)
                )
                break
        
        logger.info(
            "scraper.completed",
            source_name=self.source_name,
            total_results=len(results),
            pages_scraped=page_num
        )
        
        return results
