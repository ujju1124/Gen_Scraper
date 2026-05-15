"""
BookingComScraper - Booking.com Scraper Implementation

This module implements the scraper for Booking.com hotel listings.
It extracts hotel data using data-testid selectors and JSON-LD structured data.
Supports detail page scraping for enriched data (amenities, reviews, check-in times).
"""

import json
import random
import re
import time
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import quote_plus

import structlog
from sqlalchemy.orm import Session

from config import settings
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
            
            # Navigate to search results with timeout
            try:
                await page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
            except Exception as e:
                logger.error(
                    "scraper.navigation_failed",
                    source_name=self.source_name,
                    url=search_url,
                    error=str(e)
                )
                return []
            
            # Handle cookie consent banner if present
            # Try multiple consent button selectors (different regions use different buttons)
            consent_selectors = [
                'button[id="onetrust-accept-btn-handler"]',
                'button[id="didomi-notice-agree-button"]',
                'button:has-text("Accept")',
                'button:has-text("I agree")',
                'button:has-text("Accept all")',
            ]
            
            consent_clicked = False
            for selector in consent_selectors:
                try:
                    btn = await page.wait_for_selector(selector, timeout=3000)
                    if btn and await btn.is_visible():
                        await btn.click()
                        # Wait for actual navigation to complete (not fixed timeout)
                        await page.wait_for_load_state('domcontentloaded', timeout=15000)
                        # Small buffer after load
                        await page.wait_for_timeout(2000)
                        logger.info(
                            "scraper.cookie_consent_accepted",
                            source_name=self.source_name,
                            selector=selector
                        )
                        consent_clicked = True
                        break
                except Exception:
                    continue
            
            if not consent_clicked:
                logger.info(
                    "scraper.no_cookie_consent_banner",
                    source_name=self.source_name
                )
            
            # Now wait for property cards with timeout
            try:
                await page.wait_for_selector('[data-testid="property-card"]', timeout=15000)
                cards = await page.query_selector_all('[data-testid="property-card"]')
                logger.info(
                    "scraper.cards_found",
                    source_name=self.source_name,
                    card_count=len(cards)
                )
            except Exception as e:
                # Log current page state for debugging
                title = await page.title()
                url = page.url
                logger.error(
                    "scraper.cards_not_found",
                    source_name=self.source_name,
                    page_title=title,
                    page_url=url,
                    error=str(e)
                )
                return []
            
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
                    hotel_data = await self._extract_hotel_data(card, page, source, db, location)
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
                            break  # Break to allow detail extraction
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
            max_load_more = 5  # Reduced from 20 to prevent hangs
            consecutive_no_change = 0
            pagination_start_time = time.time()
            max_pagination_time = 60  # Maximum 60 seconds for pagination
            
            logger.info(
                "scraper.starting_pagination",
                source_name=self.source_name,
                initial_results=len(results),
                dom_cards_processed=dom_cards_processed,
                max_results=max_results
            )
            
            while load_more_clicks < max_load_more:
                # Check pagination timeout
                if time.time() - pagination_start_time > max_pagination_time:
                    logger.warning(
                        "scraper.pagination_timeout",
                        source_name=self.source_name,
                        elapsed_seconds=int(time.time() - pagination_start_time),
                        results_collected=len(results)
                    )
                    break
                
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
                                hotel_data = await self._extract_hotel_data(card, page, source, db, location)
                                if hotel_data:
                                    results.append(hotel_data)
                                    if max_results and len(results) >= max_results:
                                        logger.info(
                                            "scraper.max_results_reached",
                                            source_name=self.source_name,
                                            count=len(results),
                                            max_results=max_results
                                        )
                                        break  # Break to allow detail extraction
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
                            hotel_data = await self._extract_hotel_data(card, page, source, db, location)
                            if hotel_data:
                                results.append(hotel_data)
                                if max_results and len(results) >= max_results:
                                    logger.info(
                                        "scraper.max_results_reached",
                                        source_name=self.source_name,
                                        count=len(results),
                                        max_results=max_results
                                    )
                                    break  # Break to allow detail extraction
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
            
            # DEBUG: Check if we reach detail extraction code
            logger.info("DEBUG_DETAIL_REACHED", result_count=len(results))
            
            # DETAIL PAGE SCRAPING (following Google Maps pattern)
            # Step 1: Collect detail page URLs from results
            detail_urls = []
            for result in results:
                if 'source_url' in result and result['source_url']:
                    detail_urls.append(result['source_url'])
            
            logger.info(
                "scraper.detail_urls_collected",
                source_name=self.source_name,
                url_count=len(detail_urls),
                result_count=len(results)
            )
            
            # Step 2: Limit to max_detail_pages (default 10)
            max_detail_pages = getattr(settings, 'MAX_DETAIL_PAGES_PER_JOB', 10)
            if max_detail_pages and len(detail_urls) > max_detail_pages:
                detail_urls = detail_urls[:max_detail_pages]
                logger.info(
                    "scraper.detail_urls_limited",
                    source_name=self.source_name,
                    total_urls=len(detail_urls),
                    max_detail_pages=max_detail_pages
                )
            
            # Step 3: Visit each detail page and extract enriched data
            if detail_urls:
                logger.info(
                    "scraper.starting_detail_extraction",
                    source_name=self.source_name,
                    detail_page_count=len(detail_urls)
                )
                
                await self._extract_from_detail_pages(
                    page=page,
                    source=source,
                    db=db,
                    results=results,
                    detail_urls=detail_urls
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
    
    async def _extract_hotel_data(self, card, page, source: Source, db: Session, location: str) -> Optional[dict]:
        """
        Extract hotel data from a property card element.
        
        Uses direct data-testid selectors based on actual Booking.com page structure.
        
        Args:
            card: Playwright element handle for property card
            page: Playwright page object
            source: Source model instance
            db: SQLAlchemy database session
            location: Location string for city fallback
            
        Returns:
            Dictionary of extracted hotel data, or None if extraction fails
        """
        data = {
            "source_id": source.id,
            "currency": "NPR"  # Booking.com shows NPR for Nepal locations
        }
        
        try:
            # Extract name using data-testid="title"
            name_elem = await card.query_selector('[data-testid="title"]')
            if name_elem:
                name = await name_elem.inner_text()
                if name:
                    data["name"] = name.strip()
            
            if "name" not in data:
                logger.warning(
                    "scraper.critical_field_missing",
                    field="name",
                    source_id=source.id,
                    message="Name extraction failed"
                )
                return None
            
            # Extract rating_overall using data-testid="review-score"
            # Structure: <div data-testid="review-score"><div>Scored 9.2</div><div>9.2</div><div>Superb<br>43 reviews</div></div>
            rating_elem = await card.query_selector('[data-testid="review-score"]')
            if rating_elem:
                rating_text = await rating_elem.inner_text()
                if rating_text:
                    # Extract rating number (e.g., "9.2")
                    rating_match = re.search(r'(\d+\.?\d*)', rating_text)
                    if rating_match:
                        data["rating_overall"] = float(rating_match.group(1))
                    
                    # Extract review count
                    review_match = re.search(r'(\d+)\s*reviews?', rating_text, re.IGNORECASE)
                    if review_match:
                        data["review_count"] = int(review_match.group(1))
            
            # Extract price using data-testid="availability-rate-information"
            price_elem = await card.query_selector('[data-testid="availability-rate-information"]')
            if price_elem:
                price_text = await price_elem.inner_text()
                if price_text:
                    # Extract number from "NPR 3,334" or "NPR 3334" or "$150"
                    price_clean = re.sub(r'[^\d.]', '', price_text)
                    if price_clean:
                        try:
                            data["price_min"] = float(price_clean)
                        except ValueError:
                            pass
            
            # Extract address using data-testid="address-link"
            address_elem = await card.query_selector('[data-testid="address-link"]')
            if address_elem:
                address_text = await address_elem.inner_text()
                if address_text:
                    # Clean up address (may contain "Show on map" or similar)
                    address = address_text.replace('· Show on map', '').replace('Show on map', '').strip()
                    if address:
                        data["address"] = address
                        # Extract city (last part after comma)
                        parts = address.split(',')
                        if len(parts) >= 2:
                            data["city"] = parts[-1].strip()
                        else:
                            data["city"] = address.strip()
            
            # Fallback city to search location
            if "city" not in data:
                data["city"] = location
            
            # Extract thumbnail_url from first image in card
            img_elem = await card.query_selector('img')
            if img_elem:
                src = await img_elem.get_attribute('src')
                if src:
                    data["thumbnail_url"] = src
            
            # Extract star_rating using data-testid="rating-stars"
            # Count SVG elements and divide by 2 (Booking.com uses 2 SVGs per star)
            star_elem = await card.query_selector('[data-testid="rating-stars"]')
            if star_elem:
                svg_elements = await star_elem.query_selector_all('svg')
                if svg_elements:
                    star_count = len(svg_elements) // 2
                    if star_count > 0:
                        data["star_rating"] = star_count
            
            # Fallback: Try aria-label method
            if "star_rating" not in data:
                star_button = await card.query_selector('button[aria-label*="out of"]')
                if star_button:
                    aria_label = await star_button.get_attribute('aria-label')
                    if aria_label:
                        # Extract first number from "4 out of 5"
                        star_match = re.search(r'(\d+)', aria_label)
                        if star_match:
                            try:
                                data["star_rating"] = int(star_match.group(1))
                            except ValueError:
                                pass
            
            # Extract amenities - look for facility icons with text
            # Pattern: <div><img/><div>Bar</div></div>
            amenity_list = []
            amenity_containers = await card.query_selector_all('[data-testid="property-card"] > div > div')
            for container in amenity_containers:
                # Check if container has an img and text
                img = await container.query_selector('img')
                if img:
                    text_elem = await container.query_selector('div')
                    if text_elem:
                        text = await text_elem.inner_text()
                        if text and len(text) < 50:  # Reasonable amenity name length
                            amenity_list.append(text.strip())
            
            if amenity_list:
                data["amenities"] = ", ".join(amenity_list[:5])  # Limit to first 5
            
            # Extract source_url from title link
            if name_elem:
                href = await name_elem.get_attribute('href')
                if not href:
                    # Try parent link
                    parent = await name_elem.evaluate_handle('el => el.closest("a")')
                    if parent:
                        href = await parent.get_attribute('href')
                
                if href:
                    # Clean URL
                    href_clean = href.split('?')[0]
                    if href_clean.startswith('/'):
                        data["source_url"] = f"https://www.booking.com{href_clean}"
                    else:
                        data["source_url"] = href_clean
            
            return data
                
        except Exception as e:
            logger.warning(
                "scraper.card_extraction_error",
                source_id=source.id,
                error=str(e)
            )
            return None
    
    async def _extract_from_detail_pages(
        self,
        page,
        source: Source,
        db: Session,
        results: list[dict],
        detail_urls: list[str]
    ) -> None:
        """
        Visit each hotel detail page and extract enriched data.
        Updates the results list in-place with additional fields.
        
        Following Google Maps pattern:
        - Visit each detail URL with delays
        - Extract additional fields (amenities, reviews, check-in times)
        - Merge with existing card data by matching source_url
        
        Args:
            page: Playwright page object
            source: Source model instance
            db: SQLAlchemy database session
            results: List of hotel dictionaries (modified in-place)
            detail_urls: List of detail page URLs to visit
        """
        delay_min = getattr(settings, 'DETAIL_PAGE_DELAY_MIN', 3000)
        delay_max = getattr(settings, 'DETAIL_PAGE_DELAY_MAX', 6000)
        
        for idx, url in enumerate(detail_urls):
            try:
                logger.info(
                    "scraper.extracting_detail",
                    source_name=self.source_name,
                    index=idx + 1,
                    total=len(detail_urls),
                    url=url
                )
                
                # Navigate to detail page with timeout and error handling
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=20000)
                except Exception as e:
                    logger.warning(
                        "scraper.detail_navigation_failed",
                        source_name=self.source_name,
                        url=url,
                        error=str(e)
                    )
                    continue
                
                # Random delay between pages (3-6 seconds default)
                delay = random.randint(delay_min, delay_max)
                await page.wait_for_timeout(delay)
                
                # Check for CAPTCHA
                if await self._detect_captcha(page):
                    logger.warning(
                        "scraper.captcha_detected_on_detail",
                        source_name=self.source_name,
                        results_processed=idx
                    )
                    # Stop detail extraction but keep card data
                    break
                
                # Wait for main content - use verified selector
                try:
                    await page.wait_for_selector('h2, [data-testid="property-header"], .pp-header__title', timeout=15000)
                except Exception:
                    # Page may have loaded without this selector
                    # Continue anyway and try extraction
                    logger.warning(
                        "scraper.detail_selector_timeout",
                        source_name=self.source_name,
                        url=url
                    )
                    # Do NOT continue — still attempt extraction
                
                # Extract detail page data
                detail_data = await self._extract_detail_page_data(page, source, db)
                
                if detail_data:
                    # Find matching result by source_url and merge
                    for result in results:
                        if result.get('source_url') == url:
                            result.update(detail_data)
                            logger.debug(
                                "scraper.detail_data_merged",
                                source_name=self.source_name,
                                name=result.get('name'),
                                fields_added=list(detail_data.keys())
                            )
                            break
                
            except Exception as e:
                logger.warning(
                    "scraper.detail_extraction_error",
                    source_name=self.source_name,
                    url=url,
                    error=str(e)
                )
                continue
        
        logger.info(
            "scraper.detail_extraction_complete",
            source_name=self.source_name,
            pages_visited=len(detail_urls)
        )
    
    async def _extract_detail_field(
        self,
        page,
        source: Source,
        db: Session,
        field_name: str
    ) -> Optional[str]:
        """
        Extract a field from detail page using DB selector.
        
        This is a simplified version of _extract_field_with_healing for detail pages.
        Does NOT trigger healing (healing should only happen on card extraction).
        
        Args:
            page: Playwright page object
            source: Source model instance
            db: SQLAlchemy database session
            field_name: Name of the field to extract
            
        Returns:
            Extracted text value or None
        """
        selector_record = self.selectors.get(field_name)
        if not selector_record:
            return None
        
        try:
            elem = await page.query_selector(selector_record.selector)
            if elem:
                text = await elem.text_content()
                return text.strip() if text else None
        except Exception as e:
            logger.debug(
                "selector.detail_field_error",
                field=field_name,
                error=str(e)
            )
        
        return None
    
    async def _extract_detail_page_data(
        self,
        page,
        source: Source,
        db: Session
    ) -> dict:
        """
        Extract enriched data from hotel detail page.
        
        Extracts:
        - Full amenities list
        - Review score breakdown (Staff, Location, etc.)
        - Check-in/check-out times
        - Languages spoken
        - JSON-LD structured data (address, rating)
        
        Args:
            page: Playwright page object
            source: Source model instance
            db: SQLAlchemy database session
            
        Returns:
            Dictionary of enriched hotel data
        """
        data = {}
        
        try:
            # Extract from JSON-LD (most reliable for address, property_type, rating)
            try:
                json_ld_data = await page.evaluate('''() => {
                    const scripts = document.querySelectorAll('script[type="application/ld+json"]');
                    for (const s of scripts) {
                        try {
                            const d = JSON.parse(s.textContent);
                            if (d["@type"] === "Hotel" || d["@type"] === "LodgingBusiness") {
                                return {
                                    address: d.address?.streetAddress,
                                    property_type: d["@type"],
                                    description: d.description,
                                    image: d.image,
                                    rating: d.aggregateRating?.ratingValue,
                                    review_count: d.aggregateRating?.reviewCount
                                };
                            }
                        } catch(e) {}
                    }
                    return null;
                }''')
                
                if json_ld_data:
                    if json_ld_data.get('address'):
                        data['address'] = json_ld_data['address']
                    if json_ld_data.get('property_type'):
                        data['property_type'] = json_ld_data['property_type']
                    if json_ld_data.get('description'):
                        data['description_short'] = json_ld_data['description']
                    if json_ld_data.get('rating'):
                        data['rating_overall'] = float(json_ld_data['rating'])
                    if json_ld_data.get('review_count'):
                        data['review_count'] = int(json_ld_data['review_count'])
                    
                    logger.debug(
                        "detail.jsonld_extracted",
                        source_name=self.source_name,
                        fields=list(json_ld_data.keys())
                    )
            except Exception as e:
                logger.debug("detail.jsonld_failed", error=str(e))
            
            # Extract check-in/check-out times from House Rules section EARLY
            # (before other extractions that might cause page navigation issues)
            # Use the verified selector: [data-testid="property-section--content"]
            # NOTE: This selector returns multiple elements, we need to find the right one
            try:
                house_rules_selector = self.selectors.get('detail_house_rules')
                if house_rules_selector:
                    # Get ALL elements matching the selector (not just the first one)
                    elements = await page.query_selector_all(house_rules_selector.selector)
                    logger.debug("detail.house_rules_elements", count=len(elements), source_name=self.source_name)
                    
                    # Loop through elements to find the one with check-in/out info
                    for i, elem in enumerate(elements):
                        text = await elem.text_content()
                        if text and 'Check-in' in text and 'Check-out' in text:
                            logger.debug("detail.house_rules_found", element_index=i, source_name=self.source_name)
                            house_rules_text = text.strip()
                            
                            # Parse check-in time: "Check-inFrom 12:00 PM to 11:00 PM"
                            checkin_match = re.search(
                                r'Check-in\s*From\s+([\d:]+\s*[AP]M)\s+to\s+([\d:]+\s*[AP]M)', 
                                house_rules_text, 
                                re.IGNORECASE
                            )
                            if checkin_match:
                                data['checkin_time'] = f"From {checkin_match.group(1)} to {checkin_match.group(2)}"
                                logger.info("detail.checkin_extracted", time=data['checkin_time'], source_name=self.source_name)
                            
                            # Parse check-out time: "Check-outFrom 12:00 AM to 11:00 AM"
                            checkout_match = re.search(
                                r'Check-out\s*From\s+([\d:]+\s*[AP]M)\s+to\s+([\d:]+\s*[AP]M)', 
                                house_rules_text, 
                                re.IGNORECASE
                            )
                            if checkout_match:
                                data['checkout_time'] = f"From {checkout_match.group(1)} to {checkout_match.group(2)}"
                                logger.info("detail.checkout_extracted", time=data['checkout_time'], source_name=self.source_name)
                            
                            break  # Found it, stop looking
                else:
                    logger.warning("detail.house_rules_selector_missing", source_name=self.source_name)
                    
            except Exception as e:
                logger.warning("detail.house_rules_failed", error=str(e), source_name=self.source_name)
            
            # Extract amenities list
            amenities = await self._extract_amenities(page, source, db)
            if amenities:
                data['amenities'] = amenities
            
            # Extract review scores breakdown
            review_scores = await self._extract_review_scores(page, source, db)
            if review_scores:
                data['review_scores'] = review_scores
            
            # Extract JSON-LD structured data
            jsonld_data = await self._extract_jsonld_data(page)
            if jsonld_data:
                # Merge JSON-LD data (address, rating, reviews)
                if 'address' in jsonld_data and 'streetAddress' in jsonld_data['address']:
                    data['address_full'] = jsonld_data['address']['streetAddress']
                
                if 'aggregateRating' in jsonld_data:
                    rating_data = jsonld_data['aggregateRating']
                    if 'ratingValue' in rating_data:
                        data['rating_jsonld'] = float(rating_data['ratingValue'])
                    if 'reviewCount' in rating_data:
                        data['review_count_jsonld'] = int(rating_data['reviewCount'])
            
            # Extract full description (longer than card description)
            description = await self._extract_detail_field(page, source, db, 'detail_description')
            if description:
                data['description_full'] = description.strip()
            
            # Extract star rating from detail page
            star_rating_text = await self._extract_detail_field(page, source, db, 'detail_star_rating')
            if star_rating_text:
                # Extract number from "4 out of 5 stars"
                star_match = re.search(r'(\d+)', star_rating_text)
                if star_match:
                    try:
                        data['star_rating_detail'] = int(star_match.group(1))
                    except ValueError:
                        pass
            
        except Exception as e:
            logger.warning(
                "scraper.detail_page_extraction_error",
                source_name=self.source_name,
                error=str(e)
            )
        
        return data
    
    async def _extract_amenities(
        self,
        page,
        source: Source,
        db: Session
    ) -> Optional[str]:
        """
        Extract amenities list from detail page.
        
        Uses verified selector: [data-testid="property-most-popular-facilities-wrapper"] span
        
        Returns comma-separated string of unique amenities.
        """
        try:
            amenities_selector = self.selectors.get('detail_amenities')
            if not amenities_selector:
                return None
            
            amenities_elements = await page.query_selector_all(amenities_selector.selector)
            if not amenities_elements:
                return None
            
            amenities_list = []
            for elem in amenities_elements:
                text = await elem.text_content()
                if text:
                    text_clean = text.strip()
                    # Filter out empty strings and very long text (likely not amenities)
                    if text_clean and len(text_clean) < 50:
                        amenities_list.append(text_clean)
            
            if amenities_list:
                # Remove duplicates while preserving order
                unique_amenities = []
                seen = set()
                for amenity in amenities_list:
                    if amenity not in seen:
                        unique_amenities.append(amenity)
                        seen.add(amenity)
                
                # Limit to first 20 unique amenities
                return ', '.join(unique_amenities[:20])
            
        except Exception as e:
            logger.debug(
                "scraper.amenities_extraction_error",
                source_name=self.source_name,
                error=str(e)
            )
        
        return None
    
    async def _extract_review_scores(
        self,
        page,
        source: Source,
        db: Session
    ) -> Optional[dict]:
        """
        Extract review score breakdown (Staff, Location, Cleanliness, etc.).
        
        Returns dictionary like:
        {
            "Staff": 9.0,
            "Location": 9.5,
            "Cleanliness": 8.6,
            ...
        }
        """
        try:
            # Find all review subscore containers
            review_containers = await page.query_selector_all('[data-testid="review-subscore"]')
            if not review_containers:
                return None
            
            scores = {}
            
            for container in review_containers:
                try:
                    # Extract category name
                    category_elem = await container.query_selector('.d96a4619c0')
                    if not category_elem:
                        continue
                    category = await category_elem.text_content()
                    category = category.strip() if category else None
                    
                    # Extract score value
                    score_elem = await container.query_selector('.a9918d47bf.f87e152973')
                    if not score_elem:
                        continue
                    score_text = await score_elem.text_content()
                    score_text = score_text.strip() if score_text else None
                    
                    if category and score_text:
                        try:
                            score = float(score_text)
                            scores[category] = score
                        except ValueError:
                            pass
                
                except Exception as e:
                    logger.debug(
                        "scraper.review_score_item_error",
                        source_name=self.source_name,
                        error=str(e)
                    )
                    continue
            
            return scores if scores else None
            
        except Exception as e:
            logger.debug(
                "scraper.review_scores_extraction_error",
                source_name=self.source_name,
                error=str(e)
            )
        
        return None
    
    async def _extract_jsonld_data(self, page) -> Optional[dict]:
        """
        Extract JSON-LD structured data from detail page.
        
        Returns parsed JSON-LD object with address, rating, reviews.
        """
        try:
            jsonld_text = await page.evaluate('''() => {
                const script = document.querySelector('script[type="application/ld+json"]');
                return script ? script.textContent : null;
            }''')
            
            if jsonld_text:
                jsonld_data = json.loads(jsonld_text)
                return jsonld_data
        
        except Exception as e:
            logger.debug(
                "scraper.jsonld_extraction_error",
                source_name=self.source_name,
                error=str(e)
            )
        
        return None
