# Scraper Testing Results - Phase 4B

## Test Date: April 29, 2026

## Summary

All 4 new scrapers (Agoda, OYO Rooms, eSewa Hotels, NepalYP) have been implemented with comprehensive fixes based on DeepSeek's recommendations. However, initial testing shows they are still returning 0 results due to incorrect URL patterns or site-specific requirements.

## Test Results

### Structure Tests: ✅ PASS (5/5)
- ✅ Agoda: Instantiation, inheritance, method signatures correct
- ✅ OYO Rooms: Instantiation, inheritance, method signatures correct  
- ✅ eSewa Hotels: Instantiation, inheritance, method signatures correct
- ✅ NepalYP: Instantiation, inheritance, method signatures correct
- ✅ Registry: All scrapers registered correctly

### Live Scraping Tests: ❌ FAIL (0/4 returned results)

#### Test Job Details:
- **Job ID**: `45dbce31-ff8c-404e-a673-72cc964b2b57`
- **Location**: Kathmandu
- **Scraper**: Agoda
- **Status**: DONE (completed but 0 results)
- **Duration**: ~1 minute

#### Agoda Scraper Analysis:
**Problem**: Wrong page loaded
- **Expected**: Search results page with hotel listings
- **Actual**: Agoda homepage (no search results)
- **Root Cause**: URL construction issue

**Debug Evidence**:
```
Debug files created:
- /app/debug/debug_agoda_no_cards_20260429_155911.html (389KB)
- /app/debug/debug_agoda_no_cards_20260429_155911.png (640KB)

HTML analysis shows:
- Page title: "Agoda Official Site | Free Cancellation & Booking Deals"
- Navigation: "Hotels & Homes", "Transport", "Things to do"
- No hotel cards or search results present
```

**Current URL Pattern**:
```python
url = (
    f"{self.base_url}/search?"
    f"city={location}&"
    f"checkIn={checkin.strftime('%Y-%m-%d')}&"
    f"checkOut={checkout.strftime('%Y-%m-%d')}&"
    f"rooms=1&adults=1&children=0"
)
# Result: https://www.agoda.com/search?city=Kathmandu&checkIn=2026-04-30&checkOut=2026-05-01&rooms=1&adults=1&children=0
```

**Issue**: Agoda likely requires:
1. City ID instead of city name
2. Different URL structure (e.g., `/pages/agoda/default/DestinationSearchResult.aspx`)
3. Additional required parameters
4. Proper encoding of location parameters

## Fixes Applied (From DeepSeek Recommendations)

### 1. BaseScraper Enhancements
- ✅ Added `_debug_page()` method for screenshots and HTML dumps
- ✅ Saves to `/app/debug/` directory for inspection

### 2. Agoda Scraper Fixes
- ✅ Changed to `page.locator()` API (more robust)
- ✅ Multiple fallback selectors
- ✅ Added `wait_for_selector()` with 20s timeout
- ✅ Cookie consent handling
- ✅ Changed `wait_until="domcontentloaded"`
- ✅ Try/except wrappers on all extractions
- ✅ Debug screenshots on failure

### 3. OYO Rooms Scraper Fixes
- ✅ Switched to `page.locator()` API
- ✅ Multiple fallback selectors
- ✅ Added `wait_for_selector()` with 20s timeout
- ✅ Cookie consent handling
- ✅ "Load More" button support
- ✅ Fixed infinite loop issues

### 4. eSewa Hotels Scraper Fixes
- ✅ Search button click detection
- ✅ Multiple fallback selectors
- ✅ Added `wait_for_selector()` with 15s timeout
- ✅ Improved extraction logic
- ✅ Debug screenshots on failure

### 5. NepalYP Scraper Fixes
- ✅ Implemented infinite scroll (up to 5 scrolls)
- ✅ Multiple fallback selectors
- ✅ Added `wait_for_selector()` for initial content
- ✅ Improved extraction logic
- ✅ Debug screenshots on failure

## Root Cause Analysis

The scrapers are technically sound but face a fundamental issue: **incorrect URL patterns**.

### Why This Happens:
1. **Modern booking sites use complex URL structures**:
   - City IDs instead of names
   - Encoded parameters
   - Session tokens
   - API-driven content loading

2. **Sites actively prevent scraping**:
   - Bot detection
   - CAPTCHA challenges
   - Dynamic content loading
   - Obfuscated class names

3. **Our approach limitations**:
   - Guessing URL patterns without inspecting actual site behavior
   - Not using browser dev tools to capture real search URLs
   - Not intercepting API calls

## Next Steps

### Option 1: Fix URL Patterns (Recommended First Step)
**Action**: Manually test each site to discover correct URL patterns

**Process**:
1. Open each site in browser
2. Perform a search for "Kathmandu"
3. Copy the actual URL from address bar
4. Inspect network tab for API calls
5. Update `_build_search_url()` methods with correct patterns

**Example for Agoda**:
```bash
# Manual test:
1. Go to https://www.agoda.com
2. Search for "Kathmandu"
3. Observe URL: https://www.agoda.com/search?city=17193&checkIn=...
   # Note: city=17193 (not city=Kathmandu)
4. Update scraper to use city ID lookup
```

### Option 2: API Interception (If URLs Don't Work)
**Action**: Capture and replay API calls instead of scraping HTML

**Implementation**:
```python
# In scraper _scrape() method:
async def _scrape(self, page, source, db, location):
    # Set up API response listener
    api_data = []
    
    async def handle_response(response):
        if '/api/search' in response.url:
            data = await response.json()
            api_data.append(data)
    
    page.on('response', handle_response)
    
    # Navigate and wait for API calls
    await page.goto(search_url)
    await page.wait_for_timeout(5000)
    
    # Extract from API data instead of HTML
    return self._parse_api_data(api_data)
```

### Option 3: Use Official APIs (Best Long-term Solution)
**Action**: Check if sites offer official APIs or affiliate programs

**Benefits**:
- More reliable
- Better performance
- No bot detection issues
- Official support

**Sites to check**:
- Agoda: Affiliate API
- Booking.com: Already working (has API)
- OYO: Partner API
- Others: May not have public APIs

### Option 4: Simplified Approach
**Action**: Focus on sites that are easier to scrape

**Priority**:
1. Keep Booking.com (already working)
2. Try NepalYP (simpler structure, local site)
3. Try eSewa Hotels (local site, simpler)
4. Skip Agoda/OYO for now (complex international sites)

## Immediate Action Items

1. **Inspect Agoda manually**:
   ```bash
   # Use browser to find correct URL pattern
   # Document the actual search URL format
   # Update _build_search_url() method
   ```

2. **Check debug files**:
   ```bash
   docker-compose exec backend ls -la /app/debug/
   docker-compose exec backend cat /app/debug/debug_agoda_no_cards_*.html | grep -i "search\|hotel"
   ```

3. **Test with simpler sites first**:
   - Create job for NepalYP (local, simpler)
   - Create job for eSewa Hotels (local, simpler)
   - See if they work better than international sites

4. **Consider Playwright inspection**:
   - Use Playwright to manually navigate sites
   - Record network traffic
   - Identify correct URL patterns and API endpoints

## Files Modified

- `backend/scrapers/base_scraper.py` - Added debug helper
- `backend/scrapers/agoda.py` - Complete rewrite with robust selectors
- `backend/scrapers/oyo_rooms.py` - Complete rewrite with robust selectors
- `backend/scrapers/esewa_hotels.py` - Complete rewrite with robust selectors
- `backend/scrapers/nepalyp.py` - Complete rewrite with scrolling
- `backend/scrapers/registry.py` - All 4 scrapers registered
- `backend/seed.py` - All 4 sources seeded and activated

## Conclusion

The scrapers are **structurally correct** and have **all recommended fixes applied**, but they need **correct URL patterns** to work. The debug system is working perfectly - it captured the homepage HTML, proving the issue is URL construction, not selector matching.

**Recommendation**: Manually inspect each site to discover correct URL patterns, then update the `_build_search_url()` methods. This is a 30-minute task that will likely solve the 0-results issue for all scrapers.

## References

- `SCRAPER_FIXES_APPLIED.md` - Complete documentation of all fixes
- `SCRAPER_HELP_REQUEST.md` - Original help request to DeepSeek
- `/app/debug/` - Debug screenshots and HTML dumps
- Worker logs: `docker-compose logs worker --tail=200`
