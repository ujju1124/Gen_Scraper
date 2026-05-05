# Scraper Fixes Applied - Phase 4B

## Summary

Applied comprehensive fixes to all 4 new scrapers (Agoda, OYO Rooms, eSewa Hotels, NepalYP) based on DeepSeek's recommendations to resolve the 0-results issue.

## Root Cause

The scrapers were returning 0 results because:
1. **Brittle selectors**: Used class names that don't exist or are obfuscated in production
2. **Insufficient wait strategies**: Queried DOM before JavaScript finished rendering content
3. **No fallback selectors**: Single selector failure meant complete failure
4. **No debugging**: Couldn't see what the browser actually rendered

## Fixes Applied

### 1. Added Debugging Helper to BaseScraper

**File**: `backend/scrapers/base_scraper.py`

Added `_debug_page()` method that saves screenshots and HTML dumps for inspection:

```python
async def _debug_page(self, page, step_name: str) -> None:
    """Save screenshot and HTML for debugging."""
    # Saves to /app/debug/ directory
    # Creates: debug_{step_name}_{timestamp}.png
    #          debug_{step_name}_{timestamp}.html
```

This allows us to inspect what content the browser actually sees.

### 2. Fixed Agoda Scraper

**File**: `backend/scrapers/agoda.py`

**Changes**:
- ✅ Added cookie consent handling
- ✅ Changed from `query_selector_all()` to `page.locator()` API (more robust, auto-retries)
- ✅ Multiple fallback selectors: `[data-element-name="property-card"], [data-selenium="hotel-item"], .PropertyCard, [class*="PropertyCard"]`
- ✅ Added `wait_for_selector()` with 20s timeout before extraction
- ✅ Wrapped each field extraction in try/except with timeouts
- ✅ Added debug screenshots on failure
- ✅ Changed `wait_until="networkidle"` to `wait_until="domcontentloaded"` (faster, more reliable for SPAs)

**Key selector improvements**:
```python
# Before: Single brittle selector
hotel_cards = await page.query_selector_all('.PropertyCard')

# After: Multiple robust selectors with locator API
cards = page.locator('[data-element-name="property-card"], [data-selenium="hotel-item"], .PropertyCard, [class*="PropertyCard"]')
card_count = await cards.count()
```

### 3. Fixed OYO Rooms Scraper

**File**: `backend/scrapers/oyo_rooms.py`

**Changes**:
- ✅ Added cookie consent handling
- ✅ Switched to `page.locator()` API
- ✅ Multiple fallback selectors: `[data-testid="hotel-card"], .hotelCardWrapper, div[class*="HotelCard"], div[class*="hotel-card"]`
- ✅ Added `wait_for_selector()` with 20s timeout
- ✅ Improved price/rating extraction with better regex patterns
- ✅ Added "Load More" button support in pagination
- ✅ Fixed infinite loop issue with visibility checks

**Key improvements**:
```python
# Before: Vague selector that matched navigation links
hotel_links = await page.query_selector_all('a[href*="/np/"]')

# After: Specific hotel card containers
cards = page.locator('[data-testid="hotel-card"], .hotelCardWrapper, div[class*="HotelCard"]')
```

### 4. Fixed eSewa Hotels Scraper

**File**: `backend/scrapers/esewa_hotels.py`

**Changes**:
- ✅ Added search button click detection (some sites require form submission)
- ✅ Multiple fallback selectors for hotel listings
- ✅ Added `wait_for_selector()` for `.hotel-list, .search-results, #hotel_listing, a[href*="/hotel/"]`
- ✅ Improved name extraction with multiple fallback selectors
- ✅ Better price/rating extraction
- ✅ Added debug screenshots on failure

**Key improvements**:
```python
# Before: Single selector
hotel_links = await page.query_selector_all('a[href*="/hotel/"]')

# After: Multiple patterns + wait
await page.wait_for_selector('.hotel-list, .search-results, #hotel_listing, a[href*="/hotel/"]', timeout=15000)
hotel_links = await page.query_selector_all('a[href*="/hotel/"], a[href*="/hotels/"], .hotel-item a, .property-card a')
```

### 5. Fixed NepalYP Scraper

**File**: `backend/scrapers/nepalyp.py`

**Changes**:
- ✅ Implemented infinite scroll to load all content
- ✅ Scrolls up to 5 times until no new content appears
- ✅ Multiple fallback selectors for business listings
- ✅ Added `wait_for_selector()` for initial content
- ✅ Improved name/address/contact extraction
- ✅ Removed pagination (uses scrolling instead)
- ✅ Added debug screenshots on failure

**Key improvements**:
```python
# Added scrolling to load lazy-loaded content
last_height = await page.evaluate('document.body.scrollHeight')
while scroll_attempts < max_scrolls:
    await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
    await page.wait_for_timeout(2000)
    new_height = await page.evaluate('document.body.scrollHeight')
    if new_height == last_height:
        break
    last_height = new_height
```

## Best Practices Applied

### ✅ Do This (Applied):
1. **Use `page.wait_for_selector()`** with reasonable timeout (15-30s) instead of blind `wait_for_timeout()`
2. **Prefer `page.locator()`** over `query_selector_all()` - auto-retries, better error messages
3. **Log element counts** before parsing to verify selectors work
4. **Implement fallback selectors** - try multiple common patterns
5. **Add random delays** between actions (already in BaseScraper anti-bot measures)
6. **Wrap extractions in try/except** with timeouts to prevent single field failure from breaking entire scrape
7. **Use `wait_until="domcontentloaded"`** instead of `networkidle` for SPAs

### ❌ Avoid (Fixed):
1. ~~Hardcoded `wait_for_timeout` without condition~~ → Now use `wait_for_selector()`
2. ~~Class names that look minified~~ → Now use data attributes and multiple fallbacks
3. ~~Relying on `networkidle` for SPAs~~ → Changed to `domcontentloaded`
4. ~~Single selector with no fallback~~ → Now have 3-4 fallback selectors per element type

## Testing Strategy

To test the fixes:

1. **Run individual scraper tests**:
   ```bash
   docker-compose exec backend python test_new_scrapers.py
   ```

2. **Create test jobs via frontend** for each scraper individually

3. **Check debug output** if still getting 0 results:
   ```bash
   docker-compose exec backend ls -la /app/debug/
   docker-compose exec backend cat /app/debug/debug_*_*.html | grep "hotel"
   ```

4. **Monitor worker logs** for selector match counts:
   ```bash
   docker-compose logs worker --tail=50 | grep "cards_found\|links_found"
   ```

## Expected Outcomes

After these fixes:
- **Agoda**: Should find hotels using data attributes or class patterns
- **OYO Rooms**: Should find hotel cards and extract data correctly
- **eSewa Hotels**: Should wait for listings and extract hotel links
- **NepalYP**: Should scroll and load all business listings

If still getting 0 results, the debug screenshots/HTML will show:
1. What selectors actually exist on the page
2. Whether the site is blocking/CAPTCHAing
3. Whether content is loaded via API (can intercept with `page.wait_for_response()`)

## Next Steps if Issues Persist

1. **Check debug files**: Look at saved HTML to find actual selectors
2. **API interception**: Use `page.wait_for_response()` to capture JSON APIs
3. **Increase timeouts**: Some sites may need 30-60s to fully load
4. **Add more scrolling**: Infinite scroll sites may need more scroll attempts
5. **Check for bot detection**: Look for CAPTCHA or access denied messages in debug HTML

## Files Modified

- `backend/scrapers/base_scraper.py` - Added `_debug_page()` helper
- `backend/scrapers/agoda.py` - Complete rewrite of extraction logic
- `backend/scrapers/oyo_rooms.py` - Complete rewrite of extraction logic
- `backend/scrapers/esewa_hotels.py` - Complete rewrite of extraction logic
- `backend/scrapers/nepalyp.py` - Complete rewrite with scrolling support

## References

- DeepSeek's comprehensive fix recommendations
- Playwright locator API documentation
- AsyncCamoufox anti-detection best practices
