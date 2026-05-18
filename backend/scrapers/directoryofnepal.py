"""
DirectoryOfNepal Scraper

This scraper targets DirectoryOfNepal.com for business listings across multiple categories.
URL pattern: https://www.directoryofnepal.com/category.php?submajorid={id}&submajorname={category}&district={city}
Pagination: Static HTML with span#table-example_next a
Technology: httpx + BeautifulSoup (no JavaScript rendering needed)

This scraper is designed to be reusable across multiple categories:
- Hotels (submajorid=213)
- Restaurants (submajorid=213, minorid=670)
- Pharmacies (submajorid=1, minorid=193)

The category is extracted from the source_name (e.g., "directoryofnepal_hotels" → "Hotels")

Two-pass approach:
1. Collect all listings from listing pages (name, address, source_url, description)
2. Visit each detail page for phone, website, email, full address
"""

import structlog
import httpx
import asyncio
from typing import Optional
from sqlalchemy.orm import Session
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from scrapers.base_scraper import BaseScraper
from models.source import Source

logger = structlog.get_logger()


class DirectoryOfNepalScraper(BaseScraper):
    """
    Scraper for DirectoryOfNepal.com business listings.
    
    Target URL: https://www.directoryofnepal.com/category.php?submajorid={id}&submajorname={category}&district={city}
    Pagination: &page=1, &page=2, etc.
    Technology: httpx + BeautifulSoup (static HTML)
    
    This scraper is reusable across multiple categories by varying the source_name:
    - directoryofnepal_hotels
    - directoryofnepal_restaurants
    - directoryofnepal_pharmacies
    """
    
    # Category mapping: source_name suffix → (submajorname, submajorid, minorid)
    # Hotels & Resorts is the main category (submajorid=213)
    # Restaurants are a sub-category of Hotels & Resorts (submajorid=213, minorid=670)
    # Pharmacies are a sub-category of Emergency Health Services (submajorid=1, minorid=193)
    CATEGORY_MAP = {
        "hotels": ("Hotels & Resorts", 213, None),
        "restaurants": ("Restaurants & Bars", 213, 670),  # Sub-category of Hotels & Resorts
        "pharmacies": ("Emergency Health Services", 1, 193),  # Sub-category with minorid=193
    }
    
    def __init__(self, source_name: str = "directoryofnepal_hotels"):
        super().__init__()
        self.source_name = source_name  # Can be overridden for different categories
    
    def _get_category_info(self) -> tuple[str, Optional[int], Optional[int]]:
        """
        Extract category information from source_name.
        
        Returns:
            Tuple of (submajorname, submajorid, minorid)
            
        Examples:
            "directoryofnepal_hotels" → ("Hotels & Resorts", 213, None)
            "directoryofnepal_restaurants" → ("Restaurants & Bars", 213, 670)
        """
        # Extract suffix after "directoryofnepal_"
        if "_" in self.source_name:
            suffix = self.source_name.split("_", 1)[1]
            return self.CATEGORY_MAP.get(suffix, ("Hotels & Resorts", 213, None))
        
        # Default to Hotels & Resorts if no suffix
        return ("Hotels & Resorts", 213, None)
    
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
        Scrape business listings from DirectoryOfNepal using two-pass approach.
        
        Pass 1: Collect all listings from listing pages (name, address, source_url, description)
        Pass 2: Visit each detail page for phone, website, email, full address
        
        Args:
            page: Playwright page object (unused for httpx scraper, but required by BaseScraper interface)
            source: Source model instance
            db: SQLAlchemy database session
            location: District name (e.g., "Kathmandu", "Pokhara")
            max_results: Maximum number of results to collect (None = unlimited)
            
        Returns:
            List of scraped business dictionaries
        """
        
        # Get category info from source_name
        submajorname, submajorid, minorid = self._get_category_info()
        
        # Build base URL based on whether it's a sub-category
        if minorid:
            base_url = f"https://www.directoryofnepal.com/category.php?submajorid={submajorid}&submajorname=Hotels&minorid={minorid}&minorname={submajorname.replace(' ', '+')}&district={location}"
        else:
            base_url = f"https://www.directoryofnepal.com/category.php?submajorid={submajorid}&submajorname={submajorname}&district={location}"
        
        logger.info(
            f"directoryofnepal.starting_scrape category={submajorname} location={location} base_url={base_url}"
        )
        
        results = []
        listings = []  # Store basic listing info from listing pages
        
        # Headers to mimic browser
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True, headers=headers) as client:
            # ============================================================
            # PASS 1: Collect all listings from listing pages
            # ============================================================
            page_num = 1
            current_url = base_url
            previous_url = None
            seen_urls = set()  # Track URLs to prevent duplicates
            
            while True:
                logger.info(f"directoryofnepal.scraping_page page={page_num} url={current_url}")
                
                try:
                    response = await client.get(current_url)
                    response.raise_for_status()
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Find all listing cards (h2 a contains the name and link)
                    name_links = soup.select('h2 a')
                    
                    if not name_links:
                        logger.info(f"directoryofnepal.no_listings_found page={page_num}")
                        break
                    
                    logger.info(f"directoryofnepal.found_listings count={len(name_links)} page={page_num}")
                    
                    # Extract basic info from each listing
                    for link in name_links:
                        try:
                            name = link.get_text(strip=True)
                            source_url = urljoin("https://www.directoryofnepal.com/", link.get('href', ''))
                            
                            # Skip if URL already seen (prevents duplicates from pagination overlap)
                            if source_url in seen_urls:
                                logger.debug(f"directoryofnepal.duplicate_url_skipped url={source_url}")
                                continue
                            seen_urls.add(source_url)
                            
                            # Find the parent container to get address and description
                            # The structure is typically: h2 a (name), p.addr (address), p (description)
                            parent = link.find_parent()
                            if parent:
                                parent = parent.find_parent()  # Go up one more level
                            
                            address = None
                            description = None
                            
                            if parent:
                                # Find address (p.addr)
                                addr_elem = parent.select_one('p.addr')
                                if addr_elem:
                                    address = addr_elem.get_text(strip=True)
                                
                                # Find description (p after p.descr or just p)
                                desc_paragraphs = parent.find_all('p')
                                for p in desc_paragraphs:
                                    # Skip if it's the address paragraph
                                    if p.get('class') and 'addr' in p.get('class'):
                                        continue
                                    # Take the first non-address paragraph as description
                                    text = p.get_text(strip=True)
                                    if text and text != address:
                                        description = text
                                        break
                            
                            listing = {
                                'name': name,
                                'source_url': source_url,
                                'address': address,
                                'description': description
                            }
                            
                            listings.append(listing)
                            
                            # Check max_results limit
                            if max_results and len(listings) >= max_results:
                                logger.info(f"directoryofnepal.max_results_reached count={len(listings)}")
                                break
                        
                        except Exception as e:
                            logger.warning(f"directoryofnepal.listing_extraction_failed error={str(e)}")
                            continue
                    
                    # Stop if we reached max_results
                    if max_results and len(listings) >= max_results:
                        break
                    
                    # Check for next page button
                    next_button = soup.select_one('span#table-example_next a')
                    
                    if not next_button:
                        logger.info(f"directoryofnepal.no_next_button final_page={page_num}")
                        break
                    
                    next_href = next_button.get('href', '')
                    if not next_href:
                        logger.info(f"directoryofnepal.next_button_no_href final_page={page_num}")
                        break
                    
                    next_url = urljoin("https://www.directoryofnepal.com/", next_href)
                    
                    # Stop if URL hasn't changed (prevents infinite loop)
                    if next_url == current_url or next_url == previous_url:
                        logger.info(f"directoryofnepal.url_unchanged final_page={page_num}")
                        break
                    
                    previous_url = current_url
                    current_url = next_url
                    page_num += 1
                
                except httpx.HTTPError as e:
                    logger.error(f"directoryofnepal.http_error page={page_num} error={str(e)}")
                    break
                except Exception as e:
                    logger.error(f"directoryofnepal.page_error page={page_num} error={str(e)}")
                    break
            
            logger.info(f"directoryofnepal.pass1_complete total_listings={len(listings)}")
            
            # ============================================================
            # PASS 2: Visit each detail page for additional info
            # ============================================================
            for idx, listing in enumerate(listings, 1):
                try:
                    detail_url = listing['source_url']
                    logger.info(f"directoryofnepal.fetching_detail index={idx}/{len(listings)} url={detail_url}")
                    
                    # Add delay between requests
                    if idx > 1:
                        await asyncio.sleep(0.5)
                    
                    response = await client.get(detail_url)
                    response.raise_for_status()
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Extract full address from div.param
                    full_address = None
                    city = location  # Default to search location
                    
                    param_divs = soup.select('div.param')
                    for div in param_divs:
                        text = div.get_text(strip=True)
                        if text.startswith('Address:'):
                            full_address = text.replace('Address:', '').strip()
                            # Extract city from address (second-to-last comma segment)
                            parts = [p.strip() for p in full_address.split(',')]
                            if len(parts) >= 2:
                                city = parts[-2].strip()
                            break
                    
                    # Extract phone numbers
                    phone_primary = None
                    phone_secondary = None
                    
                    # Find Landline phone
                    cmp_items = soup.select('div.cmp-item')
                    for item in cmp_items:
                        item_text = item.get_text()
                        if 'Landline' in item_text:
                            phone_link = item.select_one('div.val a')
                            if phone_link:
                                phone_primary = phone_link.get_text(strip=True)
                        elif 'Mobile' in item_text:
                            phone_link = item.select_one('div.val a')
                            if phone_link:
                                phone_secondary = phone_link.get_text(strip=True)
                    
                    # Extract website (exclude social media and directoryofnepal.com)
                    website = None
                    excluded_domains = [
                        'directoryofnepal.com',
                        'facebook.com',
                        'twitter.com',
                        'linkedin.com',
                        'google.com',
                        'statcounter.com'
                    ]
                    
                    all_links = soup.select('a[href^="http"]')
                    for link in all_links:
                        href = link.get('href', '')
                        # Check if any excluded domain is in the href
                        if not any(domain in href for domain in excluded_domains):
                            website = href
                            break
                    
                    # Extract email
                    email = None
                    email_link = soup.select_one('a[href^="mailto:"]')
                    if email_link:
                        email = email_link.get_text(strip=True)
                    
                    # Extract thumbnail_url (business logo/image)
                    thumbnail_url = None
                    # Look for business logo or main image
                    img_selectors = [
                        'img.business-logo',
                        'img.listing-image', 
                        '.business-image img',
                        '.logo img',
                        'img[alt*="logo"]',
                        'img[alt*="Logo"]'
                    ]
                    for selector in img_selectors:
                        img = soup.select_one(selector)
                        if img:
                            src = img.get('src')
                            if src:
                                # Make absolute URL if relative
                                if src.startswith('/'):
                                    thumbnail_url = f"https://www.directoryofnepal.com{src}"
                                elif src.startswith('http'):
                                    thumbnail_url = src
                                break
                    
                    # Extract opening_hours
                    opening_hours = None
                    # Look for business hours in various formats
                    hours_selectors = [
                        '.opening-hours',
                        '.business-hours',
                        '.hours',
                        'div.param:contains("Hours")',
                        'div.param:contains("Time")',
                        'div.param:contains("Open")'
                    ]
                    for selector in hours_selectors:
                        hours_elem = soup.select_one(selector)
                        if hours_elem:
                            hours_text = hours_elem.get_text(strip=True)
                            # Clean up the text
                            if 'Hours:' in hours_text:
                                opening_hours = hours_text.replace('Hours:', '').strip()
                            elif 'Time:' in hours_text:
                                opening_hours = hours_text.replace('Time:', '').strip()
                            elif 'Open:' in hours_text:
                                opening_hours = hours_text.replace('Open:', '').strip()
                            else:
                                opening_hours = hours_text
                            break
                    
                    # Extract established_year
                    established_year = None
                    # Look for establishment year in various formats
                    year_selectors = [
                        '.established',
                        '.since-year',
                        '.founded',
                        'div.param:contains("Established")',
                        'div.param:contains("Since")',
                        'div.param:contains("Founded")'
                    ]
                    for selector in year_selectors:
                        year_elem = soup.select_one(selector)
                        if year_elem:
                            year_text = year_elem.get_text(strip=True)
                            # Extract 4-digit year
                            import re
                            year_match = re.search(r'\b(19|20)\d{2}\b', year_text)
                            if year_match:
                                try:
                                    established_year = int(year_match.group())
                                except ValueError:
                                    pass
                            break
                    
                    # Build result dictionary
                    result = {
                        'name': listing['name'],
                        'address': full_address or listing['address'],
                        'city': city,
                        'country': 'Nepal',
                        'phone_primary': phone_primary,
                        'phone_secondary': phone_secondary,
                        'email': email,
                        'website': website,
                        'thumbnail_url': thumbnail_url,
                        'opening_hours': opening_hours,
                        'established_year': established_year,
                        'description': listing['description'],
                        'description_short': listing['description'],
                        'source_url': detail_url,
                        'category': submajorname
                    }
                    
                    results.append(result)
                    
                except httpx.HTTPError as e:
                    logger.warning(f"directoryofnepal.detail_http_error index={idx} url={listing['source_url']} error={str(e)}")
                    # Keep listing data even if detail page fails
                    result = {
                        'name': listing['name'],
                        'address': listing['address'],
                        'city': location,
                        'country': 'Nepal',
                        'phone_primary': None,
                        'phone_secondary': None,
                        'email': None,
                        'website': None,
                        'thumbnail_url': None,
                        'opening_hours': None,
                        'established_year': None,
                        'description': listing['description'],
                        'description_short': listing['description'],
                        'source_url': listing['source_url'],
                        'category': submajorname
                    }
                    results.append(result)
                except Exception as e:
                    logger.warning(f"directoryofnepal.detail_parse_error index={idx} url={listing['source_url']} error={str(e)}")
                    # Keep listing data even if detail page fails
                    result = {
                        'name': listing['name'],
                        'address': listing['address'],
                        'city': location,
                        'country': 'Nepal',
                        'phone_primary': None,
                        'phone_secondary': None,
                        'email': None,
                        'website': None,
                        'thumbnail_url': None,
                        'opening_hours': None,
                        'established_year': None,
                        'description': listing['description'],
                        'description_short': listing['description'],
                        'source_url': listing['source_url'],
                        'category': submajorname
                    }
                    results.append(result)
                    results.append(result)
        
        logger.info(f"directoryofnepal.scrape_complete total_results={len(results)}")
        return results
