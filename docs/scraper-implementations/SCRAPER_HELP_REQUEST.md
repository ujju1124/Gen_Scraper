# Help Request: Fixing Web Scrapers Returning 0 Results

## Context

I'm working on a web scraping portal built with FastAPI (backend) and React (frontend). The system uses AsyncCamoufox (headless browser) to scrape hotel data from multiple sources. I recently implemented 4 new scrapers (Agoda, OYO Rooms, eSewa Hotels, NepalYP) and they run without errors but return 0 results. The issue is that these sites use heavy JavaScript rendering and the selectors aren't matching the dynamically loaded content.

## Project Structure

```
backend/
├── scrapers/
│   ├── base_scraper.py          # Abstract base class all scrapers inherit from
│   ├── booking_com.py           # Working scraper (returns 25 results)
│   ├── agoda.py                 # NEW - returns 0 results
│   ├── oyo_rooms.py             # NEW - returns 0 results
│   ├── esewa_hotels.py          # NEW - returns 0 results
│   ├── nepalyp.py               # NEW - returns 0 results
│   ├── registry.py              # Maps source names to scraper classes
│   └── orchestrator.py          # Runs scrapers in parallel
├── models/
│   └── cleaned_result.py        # Database model for scraped data
└── tasks/
    └── scrape_task.py           # Celery task that triggers scraping
```

## How the Scraper System Works

### 1. BaseScraper (Abstract Class)
All scrapers inherit from `BaseScraper` which provides:
- AsyncCamoufox browser initialization with anti-bot measures
- Template method `run()` that orchestrates the workflow
- Abstract method `_scrape()` that subclasses must implement

**Key method signature:**
```python
async def _scrape(self, page, source: Source, db: Session, location: str) -> list[dict]:
    """
    Subclass-specific scraping logic.
    
    Args:
        page: Playwright page object (AsyncCamoufox)
        source: Source model instance from database
        db: SQLAlchemy database session
        location: Location string (e.g., "Kathmandu")
        
    Returns:
        List of dictionaries with hotel data
    """
```

### 2. Working Example: BookingComScraper
This scraper successfully extracts 25 hotels from Booking.com. Here's the pattern it uses:

```python
async def _scrape(self, page, source: Source, db: Session, location: str) -> list[dict]:
    # 1. Build search URL
    search_url = self._build_search_url(location)
    
    # 2. Navigate to page
    await page.goto(search_url, wait_until="domcontentloaded", timeout=45000)
    
    # 3. Wait for content to load
    await page.wait_for_selector('[data-testid="property-card"]', timeout=15000)
    
    # 4. Extract data
    property_cards = await page.query_selector_all('[data-testid="property-card"]')
    
    for card in property_cards:
        # Extract fields from each card
        name_elem = await card.query_selector('[data-testid="title"]')
        name = (await name_elem.text_content()).strip()
        # ... more extraction
        
        results.append({
            "name": name,
            "address": address,
            "city": location,
            "price_min": price,
            "rating_overall": rating,
            "currency": "NPR"
        })
    
    return results
```

## The Problem: New Scrapers Return 0 Results

### Current Implementation Files

**backend/scrapers/agoda.py:**
```python
class AgodaScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.source_name = "agoda"
        self.base_url = "https://www.agoda.com"
    
    async def _scrape(self, page, source: Source, db: Session, location: str) -> list[dict]:
        search_url = self._build_search_url(location)
        
        await page.goto(search_url, wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(3000)
        
        hotels = []
        page_num = 1
        max_pages = 5
        
        while page_num <= max_pages:
            page_hotels = await self._extract_hotels_from_page(page, source.id, location)
            
            if not page_hotels:
                break
            
            hotels.extend(page_hotels)
            
            has_next = await self._has_next_page(page)
            if not has_next:
                break
            
            await self._click_next_page(page)
            await page.wait_for_timeout(4000)
            page_num += 1
        
        return hotels
    
    async def _extract_hotels_from_page(self, page, source_id: int, location: str) -> List[Dict[str, Any]]:
        hotels = []
        
        # PROBLEM: This selector doesn't find any elements
        hotel_cards = await page.query_selector_all('.PropertyCard')
        
        for card in hotel_cards:
            h3 = await card.query_selector('h3')
            if not h3:
                continue
            name = await h3.inner_text()
            
            # Extract price with regex
            price_el = await card.query_selector('[class*="Price"]')
            if price_el:
                price_text = await price_el.inner_text()
                price_match = re.search(r'NPR\s*([\d,]+)', price_text)
                # ... more extraction
            
            hotels.append({
                "name": name,
                "address": address or f"{name}, {location}",
                "city": location,
                "price_min": price_min,
                "rating_overall": rating_overall,
                "currency": "NPR"
            })
        
        return hotels
    
    def _build_search_url(self, location: str) -> str:
        checkin = datetime.now() + timedelta(days=1)
        checkout = checkin + timedelta(days=1)
        
        url = (
            f"{self.base_url}/search?"
            f"city={location}&"
            f"checkIn={checkin.strftime('%Y-%m-%d')}&"
            f"checkOut={checkout.strftime('%Y-%m-%d')}&"
            f"rooms=1&adults=1&children=0"
        )
        return url
```

**backend/scrapers/oyo_rooms.py:**
```python
class OYORoomsScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.source_name = "oyo_rooms"
        self.base_url = "https://www.oyorooms.com"
    
    async def _extract_hotels_from_page(self, page, source_id: int, location: str) -> List[Dict[str, Any]]:
        hotels = []
        
        # PROBLEM: This selector doesn't find any elements
        hotel_links = await page.query_selector_all('a[href*="/np/"]')
        
        for link in hotel_links:
            href = await link.get_attribute('href')
            if not href or not re.match(r'/np/\d+/', href):
                continue
            
            h3 = await link.query_selector('h3')
            if not h3:
                continue
            name = await h3.inner_text()
            
            # ... more extraction
        
        return hotels
    
    def _build_search_url(self, location: str) -> str:
        checkin = datetime.now() + timedelta(days=1)
        checkout = checkin + timedelta(days=1)
        
        checkin_str = checkin.strftime('%d/%m/%Y')
        checkout_str = checkout.strftime('%d/%m/%Y')
        
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
```

**backend/scrapers/esewa_hotels.py:**
```python
class ESewaHotelsScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.source_name = "esewa_hotels"
        self.base_url = "https://esewahotels.com"
    
    async def _extract_hotels_from_page(self, page, source_id: int, location: str) -> List[Dict[str, Any]]:
        hotels = []
        
        # PROBLEM: This selector doesn't find any elements
        hotel_links = await page.query_selector_all('a[href*="/hotel/"]')
        
        for link in hotel_links:
            h5 = await link.query_selector('h5')
            if not h5:
                continue
            name = await h5.inner_text()
            
            # ... more extraction
        
        return hotels
    
    def _build_search_url(self, location: str) -> str:
        checkin = datetime.now() + timedelta(days=1)
        checkout = checkin + timedelta(days=1)
        
        url = (
            f"{self.base_url}/searchresults/{location}?"
            f"dest={location}&"
            f"dest_type=city&"
            f"checkin={checkin.strftime('%Y-%m-%d')}&"
            f"checkout={checkout.strftime('%Y-%m-%d')}&"
            f"adults=1&children=0&rooms=1&nationality=np"
        )
        return url
```

**backend/scrapers/nepalyp.py:**
```python
class NepalYPScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.source_name = "nepalyp"
        self.base_url = "https://www.nepalyp.com"
    
    async def _scrape(self, page, source: Source, db: Session, location: str) -> list[dict]:
        # Uses search URL discovered via Playwright
        search_url = f"{self.base_url}/nepal-business-search?services=hotels&location={location}"
        
        await page.goto(search_url, wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(2000)
        
        # ... pagination loop
    
    async def _extract_hotels_from_page(self, page, source_id: int, location: str) -> List[Dict[str, Any]]:
        hotels = []
        
        # PROBLEM: This selector doesn't find any elements
        company_links = await page.query_selector_all('a[href*="/company/"]')
        
        for link in company_links:
            name = await link.inner_text()
            # ... more extraction
        
        return hotels
```

## Test Results

When I run these scrapers:
- ✅ No errors or crashes
- ✅ Scrapers complete successfully
- ❌ `hotel_cards = []` (empty list)
- ❌ Logs show: `"no_hotels_found"`, `"scrape_complete total=0"`

The Booking.com scraper works perfectly (25 results), so the infrastructure is correct.

## What I've Tried

1. **Selector discovery via Playwright MCP**: I used Playwright to inspect the sites and found these selectors:
   - Agoda: `.PropertyCard`, `h3`, `[class*="Price"]`
   - OYO Rooms: `a[href*="/np/"]`, `h3`
   - eSewa Hotels: `a[href*="/hotel/"]`, `h5`
   - NepalYP: `a[href*="/company/"]`

2. **Wait strategies**: Tried `wait_until="networkidle"`, `wait_until="domcontentloaded"`, and `wait_for_timeout()`

3. **Browser settings**: Using AsyncCamoufox with `headless=True`, anti-bot measures enabled

## The Question

**How can I fix these scrapers to successfully extract hotel data from these JavaScript-heavy sites?**

Specifically:
1. Should I use different wait strategies or selectors?
2. Do I need to wait for specific JavaScript to execute before querying?
3. Should I take screenshots or dump HTML to debug what the page actually contains?
4. Are there better selector patterns for dynamically rendered content?
5. Should I use `page.evaluate()` to run JavaScript and extract data directly?

## Example URLs to Test

- **Agoda**: `https://www.agoda.com/search?city=Kathmandu&checkIn=2026-04-30&checkOut=2026-05-01&rooms=1&adults=1&children=0`
- **OYO Rooms**: `https://www.oyorooms.com/search/?location=Kathmandu%2C+Bagmati%2C+Nepal&city=Kathmandu&searchType=city&checkin=30/04/2026&checkout=01/05/2026&country=nepal&guests=1&rooms=1`
- **eSewa Hotels**: `https://esewahotels.com/searchresults/Kathmandu?dest=Kathmandu&checkin=2026-04-30&checkout=2026-05-01&adults=1&children=0&rooms=1`
- **NepalYP**: `https://www.nepalyp.com/nepal-business-search?services=hotels&location=Kathmandu`

## What I Need

Please provide:
1. **Corrected selector strategies** for each scraper
2. **Wait/timing strategies** to ensure JS content is loaded
3. **Code snippets** showing the fixes
4. **Debugging approach** to verify what content is actually present on the page

The goal is to get these scrapers returning actual hotel data like the Booking.com scraper does.
