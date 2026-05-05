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

        try:
            while page_num <= max_pages:
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
                page_hotels = await self._extract_hotels_from_page(page, source.id, location)

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
                        logger.info("nepalyp.scrape_complete", location=location, total=len(all_hotels))
                        return all_hotels[:max_results]

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

            logger.info("nepalyp.scrape_complete", location=location, total=len(all_hotels))
            return all_hotels

        except Exception as e:
            logger.error("nepalyp.scrape_error", location=location, error=str(e))
            await self._debug_page(page, "nepalyp_error")
            return all_hotels  # Return whatever we got before the error

    async def _extract_hotels_from_page(self, page, source_id: int, location: str) -> List[Dict[str, Any]]:
        """Extract hotel data from the current page after scrolling."""
        hotels = []

        # Find all company/business links - try multiple selectors
        company_links = await page.query_selector_all('a[href*="/company/"], .business-item a, .listing-item a, [class*="company"] a')
        logger.info("nepalyp.links_found", count=len(company_links))

        for link in company_links:
            try:
                # Extract name from link text or inner elements
                name = None
                try:
                    name_elem = await link.query_selector('h3, h4, .company-name, .title, [class*="name"]')
                    if name_elem:
                        name = await name_elem.text_content()
                    else:
                        name = await link.text_content()
                    name = name.strip() if name else None
                except Exception:
                    pass

                if not name or len(name) < 3:
                    continue

                # Filter out invalid names (UI button text)
                if name.lower().strip() in INVALID_NAMES:
                    continue

                # Find parent container for address and contact info
                try:
                    parent = await link.evaluate_handle('el => el.parentElement')
                except Exception:
                    parent = link

                # Extract address
                address = None
                try:
                    address_el = await parent.query_selector('.address, .location, [class*="address"], [class*="location"]')
                    if address_el:
                        address = await address_el.text_content()
                        address = address.strip() if address else None
                except Exception:
                    pass

                # Extract phone
                phone = None
                try:
                    phone_el = await parent.query_selector('a[href^="tel:"], .phone, [class*="phone"]')
                    if phone_el:
                        phone = await phone_el.text_content()
                        phone = phone.strip() if phone else None
                except Exception:
                    pass

                # Extract email
                email = None
                try:
                    email_el = await parent.query_selector('a[href^="mailto:"], .email, [class*="email"]')
                    if email_el:
                        email = await email_el.text_content()
                        email = email.strip() if email else None
                except Exception:
                    pass

                hotel_data = {
                    "name": name,
                    "address": address or f"{name}, {location}",
                    "city": location,
                    "phone_primary": phone,
                    "email": email,
                    "price_min": None,   # NepalYP doesn't list pricing
                    "rating_overall": None,  # NepalYP doesn't list ratings
                    "currency": "NPR",
                }

                hotels.append(hotel_data)

            except Exception as e:
                logger.warning("nepalyp.extract_hotel_error", error=str(e))
                continue

        return hotels

