"""
NepalYP (Nepal Yellow Pages) scraper implementation.

Scrapes hotel listings from NepalYP business directory.
"""
import structlog
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from models.source import Source
from scrapers.base_scraper import BaseScraper

logger = structlog.get_logger()

# Invalid names to filter out (UI button text that shouldn't be saved as business names)
INVALID_NAMES = {
    "view profile", "send enquiry", "send message",
    "add review", "write review", "contact us",
    "get directions", "call now", "visit website",
    "write a review", "suggest an edit"
}


class NepalYPScraper(BaseScraper):
    """
    Scraper for NepalYP (Nepal Yellow Pages) hotel listings.
    """
    
    # Category URL mapping for categories with non-standard URLs
    CATEGORY_URL_MAP = {
        "banks": "Bankscredit_unions",
        "travel_agents": "Travel_agents",
        "tour_operators": "Tour_operators",
        "shopping_centres": "Shopping_centres",
        "clinics": "Doctors_and_Clinics",
        "car_rental": "Car_rental",
        "bakers": "Bakers",
        "insurance": "Insurance_companies",
        "motorcycle_dealers": "Motor_cycle_dealers",
        "homestays": "Home_stays",
        "courier": "Courier_services",
    }

    def __init__(self, source_name: str = "nepalyp"):
        super().__init__()
        self.source_name = source_name
        self.base_url = "https://www.nepalyp.com"
    
    def _get_category_from_source_name(self) -> str:
        """
        Extract category from source_name for dynamic URL construction.
        
        Returns:
            Category name for URL (e.g., "Hotels", "Restaurants", "Bankscredit_unions")
            
        Examples:
            "nepalyp" → "Hotels" (default)
            "nepalyp_restaurants" → "Restaurants"
            "nepalyp_pharmacies" → "Pharmacies"
            "nepalyp_banks" → "Bankscredit_unions" (mapped)
        """
        # Extract suffix after "nepalyp_"
        if "_" in self.source_name:
            suffix = self.source_name.split("_", 1)[1]
            # Check if there's a URL mapping for this category
            if suffix in self.CATEGORY_URL_MAP:
                return self.CATEGORY_URL_MAP[suffix]
            # Otherwise capitalize first letter
            return suffix.capitalize()
        
        # Default to Hotels for backward compatibility
        return "Hotels"

    async def _scrape(self, page, source: Source, db: Session, location: str, max_results: Optional[int] = None, category_id: Optional[int] = None) -> list[dict]:
        """
        Scrape hotel listings from NepalYP.

        Args:
            page: Playwright page object
            source: Source model instance
            db: SQLAlchemy database session
            location: Location string (e.g., "Kathmandu")
            max_results: Maximum results to collect (None = scrape all 34 pages)

        Returns:
            List of scraped hotel dictionaries
        """
        logger.info("nepalyp.scrape_start", location=location, max_results=max_results)

        # Get category dynamically from source_name
        category = self._get_category_from_source_name()
        
        # NepalYP uses URL-based pagination: /category/{Category}/N/city:Location
        # Page 1 is: /category/{Category}/city:Location (no page number)
        # Page N is: /category/{Category}/N/city:Location
        # Example: Hotels has ~663 hotels for Kathmandu, ~20/page, 34 pages
        # Restaurants has 1,234 restaurants in Kathmandu, 32+ pages
        # Last page has no numeric "next" page link in pagination

        all_hotels = []
        page_num = 1
        max_pages = 40  # NepalYP typically has 30-40 pages per category
        max_results_reached = False  # Flag to track if we've hit max_results

        try:
            while page_num <= max_pages and not max_results_reached:
                # Build URL for current page with dynamic category
                if page_num == 1:
                    page_url = f"{self.base_url}/category/{category}/city:{location}"
                else:
                    page_url = f"{self.base_url}/category/{category}/{page_num}/city:{location}"

                logger.info(
                    "nepalyp.scraping_page",
                    page=page_num,
                    url=page_url,
                    category=category
                )

                await page.goto(page_url, wait_until="domcontentloaded", timeout=30000)

                # Wait for business listings to appear
                try:
                    await page.wait_for_selector(
                        'a[href*="/company/"]',
                        timeout=15000
                    )
                except Exception as e:
                    logger.warning("nepalyp.no_listings_found", page=page_num, error=str(e))
                    break

                await page.wait_for_timeout(500)

                # Extract hotels from this page
                page_hotels = await self._extract_hotels_from_page(page, source, db, location)

                # Add hotels one by one, stopping exactly at max_results
                for hotel in page_hotels:
                    all_hotels.append(hotel)
                    if max_results and len(all_hotels) >= max_results:
                        logger.info(
                            "nepalyp.max_results_reached",
                            page=page_num,
                            count=len(all_hotels),
                            max_results=max_results
                        )
                        max_results_reached = True
                        break  # Break inner loop
                
                # If max_results reached, break outer loop too
                if max_results_reached:
                    break

                logger.info(
                    "nepalyp.page_extracted",
                    page=page_num,
                    hotels_on_page=len(page_hotels),
                    total_hotels=len(all_hotels)
                )

                # Check if there's a next page by looking for a link to page_num+1
                # NepalYP pagination shows nearby page numbers as links
                # When we're on the last page, there's no link to page_num+1
                next_page_exists = await page.evaluate(f"""
                    () => {{
                        const links = Array.from(document.querySelectorAll('a'));
                        const nextPageNum = {page_num + 1};
                        // Check for a link with text matching next page number
                        return links.some(a => {{
                            const text = a.textContent.trim();
                            const href = a.href || '';
                            return text === String(nextPageNum) || href.includes('/' + nextPageNum + '/city:');
                        }});
                    }}
                """)

                if not next_page_exists:
                    logger.info(
                        "nepalyp.last_page_reached",
                        page=page_num,
                        total_hotels=len(all_hotels)
                    )
                    break

                page_num += 1

            # Collect detail URLs from results
            detail_urls = [r['detail_url'] for r in all_hotels if r.get('detail_url')]
            
            logger.info(
                "nepalyp.detail_urls_collected",
                source_name=self.source_name,
                total_hotels=len(all_hotels),
                urls_found=len(detail_urls),
                sample_hotel=all_hotels[0] if all_hotels else None,
                sample_url=detail_urls[0] if detail_urls else None
            )
            
            # Limit to max_detail_pages setting
            from config import settings
            max_detail = getattr(settings, 'MAX_DETAIL_PAGES_PER_JOB', 10)
            detail_urls = detail_urls[:max_detail]
            
            logger.info(
                "nepalyp.detail_urls_after_limit",
                source_name=self.source_name,
                max_detail=max_detail,
                urls_to_visit=len(detail_urls)
            )
            
            if detail_urls:
                logger.info(
                    "nepalyp.starting_detail_extraction",
                    source_name=self.source_name,
                    detail_page_count=len(detail_urls)
                )
                await self._extract_from_detail_pages(
                    page=page,
                    source=source,
                    db=db,
                    results=all_hotels,
                    detail_urls=detail_urls
                )

            logger.info("nepalyp.scrape_complete", location=location, total=len(all_hotels))
            return all_hotels[:max_results] if max_results else all_hotels

        except Exception as e:
            logger.error("nepalyp.scrape_error", location=location, error=str(e))
            await self._debug_page(page, "nepalyp_error")
            return all_hotels  # Return whatever we got before the error

    async def _extract_hotels_from_page(self, page, source: Source, db: Session, location: str) -> List[Dict[str, Any]]:
        """Extract hotel data from the current page using healing-enabled extraction."""
        hotels = []

        # Find all company card containers (not the links themselves)
        # Structure: <div class="company ..."><div class="company_header"><h3><a>Name</a></h3></div></div>
        cards = await page.query_selector_all('div.company, div[class*="company "]')
        
        logger.info(
            "nepalyp.cards_found",
            source_name=self.source_name,
            card_count=len(cards)
        )

        for card in cards:
            try:
                # Extract company link from card
                link = await card.query_selector('a[href*="/company/"]')
                if not link:
                    continue

                # Get detail URL
                detail_url = await link.get_attribute('href')
                if detail_url and not detail_url.startswith('http'):
                    detail_url = 'https://www.nepalyp.com' + detail_url

                # Extract name with healing - card now contains h3 a structure
                name = await self._extract_field_with_healing(
                    card=card,
                    page=page,
                    source=source,
                    db=db,
                    field_name='name'
                )

                # Fallback: get text directly from link if healing fails
                if not name:
                    name = await link.text_content()
                    name = name.strip() if name else None

                if not name or len(name) < 3:
                    continue

                # Filter out invalid names (UI button text)
                if name.lower().strip() in INVALID_NAMES:
                    continue

                # Extract address with healing
                address = await self._extract_field_with_healing(
                    card=card,
                    page=page,
                    source=source,
                    db=db,
                    field_name='address'
                )

                # Extract phone with healing
                phone = await self._extract_field_with_healing(
                    card=card,
                    page=page,
                    source=source,
                    db=db,
                    field_name='phone'
                )

                # Extract email with healing
                email = await self._extract_field_with_healing(
                    card=card,
                    page=page,
                    source=source,
                    db=db,
                    field_name='email'
                )

                hotel_data = {
                    "name": name,
                    "address": address or f"{name}, {location}",
                    "city": location,
                    "phone_primary": phone,
                    "email": email,
                    "price_min": None,   # NepalYP doesn't list pricing
                    "rating_overall": None,  # NepalYP doesn't list ratings
                    "currency": "NPR",
                    "detail_url": detail_url,  # Store for detail page extraction
                }

                hotels.append(hotel_data)

            except Exception as e:
                logger.warning("nepalyp.extract_hotel_error", error=str(e))
                continue

        # Debug logging
        logger.info(
            "nepalyp.extraction_complete",
            source_name=self.source_name,
            card_count=len(cards),
            result_count=len(hotels),
            sample_name=hotels[0].get('name') if hotels else None,
            sample_url=hotels[0].get('detail_url') if hotels else None
        )

        return hotels


    async def _extract_from_detail_pages(
        self,
        page,
        source: Source,
        db: Session,
        results: list,
        detail_urls: list
    ) -> None:
        """
        Visit each NepalYP company page and extract phone, address, website.
        
        Args:
            page: Playwright page object
            source: Source model instance
            db: SQLAlchemy database session
            results: List of result dictionaries to enrich
            detail_urls: List of detail page URLs to visit
        """
        import random
        from config import settings
        
        delay_min = getattr(settings, 'DETAIL_PAGE_DELAY_MIN', 2000)
        delay_max = getattr(settings, 'DETAIL_PAGE_DELAY_MAX', 4000)
        
        for idx, url in enumerate(detail_urls):
            try:
                logger.info(
                    "nepalyp.extracting_detail",
                    source_name=self.source_name,
                    index=idx + 1,
                    total=len(detail_urls),
                    url=url
                )
                
                await page.goto(url, wait_until='domcontentloaded', timeout=20000)
                await page.wait_for_timeout(random.randint(delay_min, delay_max))
                
                # Extract ALL phone numbers
                # Handles both "tel:number" AND "tel: number"
                phones = await page.evaluate('''() => {
                    const links = document.querySelectorAll('a[href^="tel"]');
                    const nums = new Set();
                    for (const a of links) {
                        const t = a.textContent.trim();
                        // Must be at least 7 digits
                        if (t && /\\d{7,}/.test(t)) {
                            nums.add(t);
                        }
                    }
                    return [...nums].join(", ");
                }''')
                
                # Extract address
                address = await page.evaluate('''() => {
                    const el = document.querySelector('[itemprop="address"], .address, ' +
                        '.col-address, [class*="address"]');
                    return el ? el.textContent.trim() : null;
                }''')
                
                # Extract website
                # Skip google, nepalyp, social media links
                website = await page.evaluate('''() => {
                    const skip = ["nepalyp", "google", "facebook",
                                  "twitter", "youtube", "instagram",
                                  "linkedin", "tiktok"];
                    const links = document.querySelectorAll('a[href^="http"]');
                    for (const a of links) {
                        const href = a.href.toLowerCase();
                        if (!skip.some(s => href.includes(s))) {
                            return a.href;
                        }
                    }
                    return null;
                }''')
                
                # Find matching result by detail_url and merge
                for result in results:
                    if result.get('detail_url') == url:
                        if phones:
                            result['phone_primary'] = phones
                        if address and not result.get('address'):
                            result['address'] = address.strip()
                        if website:
                            result['website'] = website
                        
                        logger.info(
                            "nepalyp.detail_merged",
                            source_name=self.source_name,
                            name=result.get('name'),
                            has_phone=bool(phones),
                            has_address=bool(address),
                            has_website=bool(website)
                        )
                        break
                        
            except Exception as e:
                logger.warning(
                    "nepalyp.detail_failed",
                    source_name=self.source_name,
                    url=url,
                    error=str(e)
                )
                continue
        
        logger.info(
            "nepalyp.detail_extraction_complete",
            source_name=self.source_name,
            pages_visited=len(detail_urls)
        )
