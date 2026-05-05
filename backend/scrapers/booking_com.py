"""
BookingComScraper - Booking.com Scraper Implementation

This module implements the scraper for Booking.com hotel listings.
It extracts hotel data using data-testid selectors and JSON-LD structured data.
"""

import re
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import quote_plus

import structlog
from sqlalchemy.orm import Session

from models.source import Source
from scrapers.base_scraper import BaseScraper

logger = structlog.get_logger()


class BookingComScraper(BaseScraper):
    """
    Scraper for Booking.com hotel listings.
    
    Extracts hotel information including:
    - Name, address, rating, reviews
    - Pricing (requires checkin/checkout dates)
    - Star rating, thumbnail images
    - Source URLs for each property
    """
    
    def __init__(self):
        """Initialize BookingComScraper."""
        super().__init__()
        self.source_name = "booking_com"
    
    async def _scrape(self, page, source: Source, db: Session, location: str, max_results: Optional[int] = None, category_id: Optional[int] = None) -> list[dict]:
        """
        Scrape Booking.com for hotel listings.
        
        Args:
            page: Playwright page object
            source: Source model instance
            db: SQLAlchemy database session
            location: Location string (e.g., "Kathmandu")
            max_results: Maximum results to collect (None = scrape all via scroll + load more)
            
        Returns:
            List of scraped hotel dictionaries
        """
        results = []
        
        try:
            # Build search URL with dynamic dates
            search_url = self._build_search_url(location)
            
            logger.info(
                "scraper.navigating",
                source_name=self.source_name,
                url=search_url,
                max_results=max_results
            )
            
            # Navigate to search results
            await page.goto(search_url, wait_until="domcontentloaded", timeout=45000)
            
            # Handle cookie consent banner if present
            try:
                # Booking.com uses OneTrust consent - accept all cookies
                consent_button = await page.wait_for_selector(
                    'button[id="onetrust-accept-btn-handler"]',
                    timeout=5000
                )
                if consent_button:
                    await consent_button.click()
                    logger.info(
                        "scraper.cookie_consent_accepted",
                        source_name=self.source_name
                    )
                    # Wait for page to reload after consent
                    await page.wait_for_timeout(3000)
            except Exception:
                # No consent banner - proceed normally
                pass
            
            # Now wait for property cards
            await page.wait_for_selector('[data-testid="property-card"]', timeout=15000)
            
            # Check for CAPTCHA
            if await self._detect_captcha(page):
                logger.warning(
                    "scraper.captcha_detected",
                    source_name=self.source_name,
                    url=search_url
                )
                return []
            
            # Extract JSON-LD data (first pass)
            html = await page.content()
            json_ld_data = self._extract_json_ld(html)
            
            # Get all property cards currently in DOM
            property_cards = await page.query_selector_all('[data-testid="property-card"]')
            
            logger.info(
                "scraper.cards_found",
                source_name=self.source_name,
                card_count=len(property_cards)
            )
            
            # Track how many DOM cards we've already processed (by index, not result count)
            # This is separate from len(results) because some cards may fail extraction
            dom_cards_processed = 0
            
            # Extract initial batch
            for idx, card in enumerate(property_cards):
                try:
                    hotel_data = await self._extract_hotel_data(card, source.id, location)
                    if hotel_data:
                        if json_ld_data and idx == 0:
                            hotel_data = {**hotel_data, **json_ld_data}
                        results.append(hotel_data)
                        if max_results and len(results) >= max_results:
                            logger.info(
                                "scraper.max_results_reached",
                                source_name=self.source_name,
                                count=len(results),
                                max_results=max_results
                            )
                            return results[:max_results]
                except Exception as e:
                    logger.warning(
                        "scraper.card_extraction_failed",
                        source_name=self.source_name,
                        card_index=idx,
                        error=str(e)
                    )
            dom_cards_processed = len(property_cards)
            
            # Booking.com uses infinite scroll + "Load more results" button
            # Behavior confirmed via Playwright live analysis:
            #   - Initial load: ~25 cards
            #   - Scroll 1: grows to ~50 cards (infinite scroll, no button yet)
            #   - Scroll 2: grows to ~75 cards, "Load more results" button appears
            #   - Each "Load more" click: adds ~25 more cards
            # Strategy:
            #   1. Scroll → if new cards appeared, extract them, keep scrolling
            #   2. When scroll stops adding cards, look for "Load more" button
            #   3. Click button → wait for new cards → extract → repeat
            #   4. Stop when: limit reached OR no new cards after click/scroll
            load_more_clicks = 0
            max_load_more = 20
            consecutive_no_change = 0
            
            logger.info(
                "scraper.starting_pagination",
                source_name=self.source_name,
                initial_results=len(results),
                dom_cards_processed=dom_cards_processed,
                max_results=max_results
            )
            
            while load_more_clicks < max_load_more:
                # Check limit before doing any more work
                if max_results and len(results) >= max_results:
                    logger.info(
                        "scraper.max_results_reached",
                        source_name=self.source_name,
                        count=len(results),
                        max_results=max_results
                    )
                    break
                
                try:
                    # --- STEP 1: Scroll to trigger infinite scroll ---
                    await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                    await page.wait_for_timeout(2500)
                    
                    all_cards_now = await page.query_selector_all('[data-testid="property-card"]')
                    total_dom_cards = len(all_cards_now)
                    
                    logger.info(
                        "scraper.scroll_result",
                        source_name=self.source_name,
                        dom_before=dom_cards_processed,
                        dom_after=total_dom_cards
                    )
                    
                    if total_dom_cards > dom_cards_processed:
                        # New cards appeared via infinite scroll — extract them
                        consecutive_no_change = 0
                        new_cards = all_cards_now[dom_cards_processed:]
                        for card in new_cards:
                            try:
                                hotel_data = await self._extract_hotel_data(card, source.id, location)
                                if hotel_data:
                                    results.append(hotel_data)
                                    if max_results and len(results) >= max_results:
                                        logger.info(
                                            "scraper.max_results_reached",
                                            source_name=self.source_name,
                                            count=len(results),
                                            max_results=max_results
                                        )
                                        return results[:max_results]
                            except Exception as e:
                                logger.warning(
                                    "scraper.card_extraction_failed",
                                    source_name=self.source_name,
                                    error=str(e)
                                )
                        dom_cards_processed = total_dom_cards
                        # Keep scrolling — more cards may load
                        continue
                    else:
                        consecutive_no_change += 1
                    
                    # --- STEP 2: Look for "Load more results" button ---
                    load_more_button = await page.query_selector('button:has-text("Load more results")')
                    if not load_more_button:
                        load_more_button = await page.query_selector('button:has-text("Load more")')
                    
                    if not load_more_button:
                        if consecutive_no_change >= 2:
                            logger.info(
                                "scraper.no_load_more_button",
                                source_name=self.source_name,
                                clicks=load_more_clicks,
                                consecutive_no_change=consecutive_no_change
                            )
                            break
                        continue  # Keep scrolling
                    
                    # Button found — check it's usable
                    if not await load_more_button.is_visible() or not await load_more_button.is_enabled():
                        logger.info(
                            "scraper.load_more_button_disabled",
                            source_name=self.source_name,
                            clicks=load_more_clicks
                        )
                        break
                    
                    consecutive_no_change = 0
                    
                    # --- STEP 3: Click and wait for new cards to appear in DOM ---
                    cards_before_click = len(await page.query_selector_all('[data-testid="property-card"]'))
                    await load_more_button.click()
                    load_more_clicks += 1
                    
                    logger.info(
                        "scraper.clicked_load_more",
                        source_name=self.source_name,
                        click_number=load_more_clicks,
                        cards_before=cards_before_click
                    )
                    
                    # Wait up to 8s for new cards to appear in DOM
                    waited = 0
                    while waited < 8000:
                        await page.wait_for_timeout(500)
                        waited += 500
                        cards_now = len(await page.query_selector_all('[data-testid="property-card"]'))
                        if cards_now > cards_before_click:
                            break  # New cards loaded
                    
                    # --- STEP 4: Extract the new cards ---
                    all_cards_now = await page.query_selector_all('[data-testid="property-card"]')
                    new_cards = all_cards_now[dom_cards_processed:]
                    
                    logger.info(
                        "scraper.cards_after_load_more",
                        source_name=self.source_name,
                        total_dom=len(all_cards_now),
                        new_cards=len(new_cards),
                        results_so_far=len(results)
                    )
                    
                    if not new_cards:
                        logger.info(
                            "scraper.no_new_cards_after_click",
                            source_name=self.source_name,
                            clicks=load_more_clicks
                        )
                        break
                    
                    for card in new_cards:
                        try:
                            hotel_data = await self._extract_hotel_data(card, source.id, location)
                            if hotel_data:
                                results.append(hotel_data)
                                if max_results and len(results) >= max_results:
                                    logger.info(
                                        "scraper.max_results_reached",
                                        source_name=self.source_name,
                                        count=len(results),
                                        max_results=max_results
                                    )
                                    return results[:max_results]
                        except Exception as e:
                            logger.warning(
                                "scraper.card_extraction_failed",
                                source_name=self.source_name,
                                load_more_round=load_more_clicks,
                                error=str(e)
                            )
                    dom_cards_processed = len(all_cards_now)
                    
                except Exception as e:
                    logger.warning(
                        "scraper.load_more_error",
                        source_name=self.source_name,
                        clicks=load_more_clicks,
                        error=str(e)
                    )
                    break
            
            logger.info(
                "scraper.extraction_complete",
                source_name=self.source_name,
                location=location,
                load_more_clicks=load_more_clicks,
                result_count=len(results)
            )
            
        except Exception as e:
            logger.error(
                "scraper.navigation_failed",
                source_name=self.source_name,
                location=location,
                error=str(e)
            )
            raise
        
        return results
    
    def _build_search_url(self, location: str) -> str:
        """
        Build Booking.com search URL with dynamic dates.
        
        Uses tomorrow as checkin and day after as checkout.
        This ensures prices are displayed in search results.
        
        Args:
            location: Location string (e.g., "Kathmandu")
            
        Returns:
            Complete search URL with encoded parameters
        """
        # Calculate dates
        today = datetime.now()
        checkin = today + timedelta(days=1)
        checkout = today + timedelta(days=2)
        
        # Format dates as YYYY-MM-DD
        checkin_str = checkin.strftime("%Y-%m-%d")
        checkout_str = checkout.strftime("%Y-%m-%d")
        
        # URL encode location with quote_plus
        location_encoded = quote_plus(location)
        
        # Build URL
        url = (
            f"https://www.booking.com/searchresults.html"
            f"?ss={location_encoded}"
            f"&checkin={checkin_str}"
            f"&checkout={checkout_str}"
            f"&group_adults=1"
            f"&no_rooms=1"
            f"&group_children=0"
        )
        
        logger.debug(
            "scraper.url_built",
            location=location,
            checkin=checkin_str,
            checkout=checkout_str,
            url=url
        )
        
        return url
    
    async def _extract_hotel_data(self, card, source_id: int, location: str) -> Optional[dict]:
        """
        Extract hotel data from a property card element.
        
        Args:
            card: Playwright element handle for property card
            source_id: ID of the source
            location: Location string for city fallback
            
        Returns:
            Dictionary of extracted hotel data, or None if extraction fails
        """
        data = {
            "source_id": source_id,
            "currency": "NPR"  # Booking.com shows NPR for Nepal locations
        }
        
        try:
            # Extract name
            name_elem = await card.query_selector('[data-testid="title"]')
            if name_elem:
                data["name"] = (await name_elem.text_content()).strip()
            
            # Extract rating_overall and review_count
            # Format: "Scored 9.7 9.7Exceptional 295 reviews"
            rating_elem = await card.query_selector('[data-testid="review-score"]')
            if rating_elem:
                rating_text = (await rating_elem.text_content()).strip()
                
                # Extract first number (rating)
                rating_match = re.search(r'(\d+\.?\d*)', rating_text)
                if rating_match:
                    data["rating_overall"] = float(rating_match.group(1))
                
                # Extract review count (last number before "reviews")
                review_match = re.search(r'(\d+)\s*reviews?', rating_text, re.IGNORECASE)
                if review_match:
                    data["review_count"] = int(review_match.group(1))
            
            # Extract price_min
            # Format: "NPR 3,334" or "NPR 3334"
            price_elem = await card.query_selector('[data-testid="price-and-discounted-price"]')
            if price_elem:
                price_text = (await price_elem.text_content()).strip()
                
                # Remove "NPR" and commas, extract number
                price_clean = re.sub(r'[^\d.]', '', price_text)
                if price_clean:
                    try:
                        data["price_min"] = float(price_clean)
                    except ValueError:
                        pass
            
            # Extract address
            address_elem = await card.query_selector('[data-testid="address-link"]')
            if address_elem:
                data["address"] = (await address_elem.text_content()).strip()
            
            # Extract city from address or use location as fallback
            if "address" in data:
                addr = data["address"]
                # Booking.com address format: "Neighbourhood, City"
                # or just "City"
                parts = addr.split(",")
                if len(parts) >= 2:
                    data["city"] = parts[-1].strip()
                else:
                    data["city"] = addr.strip()
            else:
                data["city"] = location  # fallback to search location
            
            # Extract thumbnail_url (img src attribute)
            thumbnail_elem = await card.query_selector('[data-testid="image"]')
            if thumbnail_elem:
                # Get img element inside
                img = await thumbnail_elem.query_selector('img')
                if img:
                    src = await img.get_attribute('src')
                    if src:
                        data["thumbnail_url"] = src
            
            # Set star_rating to None (not reliable from Booking.com)
            data["star_rating"] = None
            
            # Extract source_url (href of title-link)
            link_elem = await card.query_selector('[data-testid="title-link"]')
            if link_elem:
                href = await link_elem.get_attribute('href')
                if href:
                    # Strip tracking parameters
                    href_clean = href.split('?')[0]
                    
                    # Make absolute URL if relative
                    if href_clean.startswith('/'):
                        data["source_url"] = f"https://www.booking.com{href_clean}"
                    else:
                        data["source_url"] = href_clean
            
            # Only return if we have at least name
            if "name" in data:
                return data
            else:
                logger.warning(
                    "scraper.card_missing_name",
                    source_id=source_id
                )
                return None
                
        except Exception as e:
            logger.warning(
                "scraper.card_extraction_error",
                source_id=source_id,
                error=str(e)
            )
            return None
