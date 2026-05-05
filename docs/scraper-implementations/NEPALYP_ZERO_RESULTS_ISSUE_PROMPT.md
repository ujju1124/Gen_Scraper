# Issue: NepalYP Scraper Returns 0 Results for New Categories

## Context
We recently added 7 new NepalYP category sources (real_estate, petrol_stations, motorcycle_dealers, tourist_attractions, homestays, resorts, courier) following the same pattern as existing NepalYP sources (restaurants, pharmacies, banks, etc.).

The scrapers are properly registered and execute without errors, but they return 0 results even though the URLs are correct.

## What's Working
1. ✅ Scrapers are registered in `backend/scrapers/registry.py`
2. ✅ Sources are seeded in database with correct category mappings
3. ✅ Worker recognizes and executes the scrapers
4. ✅ Scrapers navigate to correct URLs (e.g., `https://www.nepalyp.com/category/Real_estate/city:Kathmandu`)
5. ✅ No errors in execution

## The Problem
When NepalYP scraper runs for new categories, it returns 0 results:

```
nepalyp.scrape_start location=Kathmandu max_results=15
nepalyp.scraping_page category=Real_estate page=1 
  url=https://www.nepalyp.com/category/Real_estate/city:Kathmandu
nepalyp.links_found count=1
nepalyp.page_extracted hotels_on_page=0 page=1 total_hotels=0
nepalyp.last_page_reached page=1 total_hotels=0
nepalyp.scrape_complete location=Kathmandu total=0
```

It finds 1 link but extracts 0 businesses.

## Reference: Google Maps Integration Success
During Phase 6, we successfully integrated Google Maps as a universal source that works across ALL categories. The key was:

1. **Dynamic Category Handling:** Google Maps scraper accepts any category_id and resolves it to the category name
2. **Universal URL Pattern:** Uses `https://www.google.com/maps/search/{category}+in+{location}/`
3. **Category Resolution:** Queries the database to get category name from category_id
4. **No Hardcoded Categories:** Works for hotels, restaurants, real_estate, tourist_places, etc.

**Google Maps Implementation (backend/scrapers/google_maps.py):**
```python
async def _scrape(self, page, source: Source, db: Session, location: str, 
                  max_results: Optional[int] = None, category_id: Optional[int] = None):
    # Resolve category from category_id
    if category_id:
        category_obj = db.query(Category).filter(Category.id == category_id).first()
        if category_obj:
            category = category_obj.name  # e.g., "real_estate", "tourist_places"
            logger.info("google_maps.category_resolved", category=category, category_id=category_id)
    
    # Build dynamic URL
    search_url = f"https://www.google.com/maps/search/{category}+in+{location}/"
    
    # Rest of scraping logic...
```

This approach made Google Maps work for ANY category without code changes.

## Current NepalYP Implementation
NepalYP scraper uses a similar pattern but might have issues:

**backend/scrapers/nepalyp.py:**
```python
def _get_category_from_source_name(self) -> str:
    """Extract category from source_name for dynamic URL construction."""
    if "_" in self.source_name:
        suffix = self.source_name.split("_", 1)[1]
        # Check if there's a URL mapping for this category
        if suffix in self.CATEGORY_URL_MAP:
            return self.CATEGORY_URL_MAP[suffix]
        # Otherwise capitalize first letter
        return suffix.capitalize()
    
    return "Hotels"  # Default

async def _scrape(self, page, source: Source, db: Session, location: str, 
                  max_results: Optional[int] = None, category_id: Optional[int] = None):
    # Get category dynamically from source_name
    category = self._get_category_from_source_name()
    
    # Build URL
    if page_num == 1:
        page_url = f"{self.base_url}/category/{category}/city:{location}"
    else:
        page_url = f"{self.base_url}/category/{category}/{page_num}/city:{location}"
    
    # Extract businesses
    page_hotels = await self._extract_hotels_from_page(page, source.id, location)
```

## Suspected Issues

### 1. Generic Selectors May Not Match All Categories
The `_extract_hotels_from_page()` method uses generic selectors:
```python
company_links = await page.query_selector_all('a[href*="/company/"], .business-item a, .listing-item a, [class*="company"] a')
```

These selectors work for Hotels/Restaurants but might not match Real Estate/Tourist Attractions page structure.

### 2. Variable Name "hotels" Used for All Categories
The code uses variable names like `hotels`, `page_hotels`, `all_hotels` even for non-hotel categories. This is just naming but might indicate the logic is too hotel-specific.

### 3. No Category-Specific Selector Handling
Unlike other scrapers that load selectors from database, NepalYP uses hardcoded selectors that might not work for all category page layouts.

## Questions for Claude

1. **Should NepalYP use database selectors like other scrapers?** 
   - Currently: Hardcoded selectors in `_extract_hotels_from_page()`
   - Alternative: Load selectors from `scraper_selectors` table per category

2. **Should we inspect actual NepalYP category pages?**
   - Visit https://www.nepalyp.com/category/Real_estate/city:Kathmandu
   - Check if HTML structure differs from Hotels category
   - Extract actual selectors that work

3. **Should we add category-specific selector logic?**
   - Like Google Maps, make it truly universal
   - Or accept that some categories might be empty on NepalYP

4. **Is the issue that categories are actually empty?**
   - NepalYP might not have Real Estate listings for Kathmandu
   - Should we test with categories known to have data first?

## What We Need

**Option A: Quick Fix**
- Test with a category known to have data (e.g., nepalyp_banks, nepalyp_schools)
- If those work, accept that some categories are empty

**Option B: Robust Solution**
- Inspect NepalYP page HTML for different categories
- Add category-specific selectors to database
- Update NepalYP scraper to load selectors from DB like other scrapers

**Option C: Hybrid Approach**
- Keep generic selectors as fallback
- Add optional category-specific selectors from database
- Log when generic selectors return 0 results for debugging

## Files to Reference

1. **backend/scrapers/google_maps.py** - Universal scraper that works for all categories
2. **backend/scrapers/nepalyp.py** - Current implementation with potential issues
3. **backend/scrapers/base_scraper.py** - Base class with selector loading logic
4. **backend/scrapers/directoryofnepal.py** - Another multi-category scraper for comparison

## Expected Outcome

After your solution, we should be able to:
1. Run a scrape job for any NepalYP category
2. Get results if the category has listings on NepalYP
3. Get 0 results gracefully if category is empty (not an error)
4. Have clear logging to distinguish between "no listings" vs "selector mismatch"

---

**Current Status:** Priority 1 & 2 complete except for verifying NepalYP data extraction  
**Next:** Priority 3 (Fuzzy Matching) - can proceed once this is resolved or confirmed as "categories are empty"
