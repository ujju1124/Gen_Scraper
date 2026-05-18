# Booking.com Detail Page Scraping Implementation

## Overview
Implemented detail page scraping for Booking.com following the Google Maps reference architecture. The scraper now:
1. Collects hotel cards from search results (existing functionality)
2. Extracts detail page URLs from each card
3. Visits up to 10 detail pages per job (configurable)
4. Extracts enriched data from detail pages
5. Merges detail data with card data

## Implementation Details

### 1. Selector Verification (Completed)
All selectors were tested in browser console on Kathmandu Guest House detail page:
- ✅ Star Rating: `[data-testid="rating-stars"]` → "4 out of 5 stars"
- ✅ Description: `[data-testid="property-description"]` → Full text
- ✅ Amenities: `#hp_facilities_box li` → List of facilities
- ✅ Review Scores: `[data-testid="review-subscore"]` with `.d96a4619c0` (category) and `.a9918d47bf.f87e152973` (score)
- ✅ JSON-LD: `script[type="application/ld+json"]` → Address, rating, review count
- ✅ Check-in: `DIV.b99b6ef58f` → Time range
- ✅ Check-out: `DIV.b99b6ef58f` → Time range
- ✅ Languages: `SPAN.f6b6d2a959` → Languages spoken

### 2. Database Selectors (SQL File Created)
File: `add_booking_detail_selectors.sql`

Adds 9 new selectors to `scraper_selectors` table:
- `detail_star_rating`
- `detail_description`
- `detail_amenities`
- `detail_review_category`
- `detail_review_score`
- `detail_checkin`
- `detail_checkout`
- `detail_languages`
- `detail_jsonld`

**To apply:**
```bash
docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -f /app/add_booking_detail_selectors.sql
```

Or copy the file into the container first:
```bash
docker cp add_booking_detail_selectors.sql gen_scraper-postgres-1:/tmp/
docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -f /tmp/add_booking_detail_selectors.sql
```

### 3. Configuration Added

**`.env` additions:**
```env
# Detail Page Scraping Configuration
MAX_DETAIL_PAGES_PER_JOB=10
DETAIL_PAGE_DELAY_MIN=3000
DETAIL_PAGE_DELAY_MAX=6000
```

**`config.py` additions:**
```python
# Detail page scraping settings
MAX_DETAIL_PAGES_PER_JOB: int = 10
DETAIL_PAGE_DELAY_MIN: int = 3000  # milliseconds
DETAIL_PAGE_DELAY_MAX: int = 6000  # milliseconds
```

### 4. Code Changes

**`booking_com.py` - New Methods:**

1. **`_extract_from_detail_pages()`**
   - Visits each detail URL with random delays (3-6 seconds)
   - Extracts enriched data from each page
   - Merges data with existing results by matching source_url
   - Handles CAPTCHA detection (stops if detected)

2. **`_extract_detail_page_data()`**
   - Orchestrates extraction of all detail page fields
   - Returns dictionary of enriched data

3. **`_extract_amenities()`**
   - Extracts list of amenities/facilities
   - Returns comma-separated string (up to 20 items)

4. **`_extract_review_scores()`**
   - Extracts review score breakdown (Staff, Location, Cleanliness, etc.)
   - Returns dictionary: `{"Staff": 9.0, "Location": 9.5, ...}`

5. **`_extract_jsonld_data()`**
   - Extracts JSON-LD structured data
   - Returns parsed JSON with address, rating, review count

**Updated `_scrape()` method:**
- After collecting all cards, extracts detail URLs
- Limits to `MAX_DETAIL_PAGES_PER_JOB` (default 10)
- Calls `_extract_from_detail_pages()` to enrich data

### 5. Data Fields Extracted from Detail Pages

**New fields added to results:**
- `amenities` - Comma-separated list of facilities
- `review_scores` - Dictionary of category scores
- `checkin_time` - Check-in time range
- `checkout_time` - Check-out time range
- `languages` - Languages spoken at property
- `address_full` - Full address from JSON-LD
- `rating_jsonld` - Rating from JSON-LD (may differ from card rating)
- `review_count_jsonld` - Review count from JSON-LD
- `description_full` - Full description (longer than card description)
- `star_rating_detail` - Star rating from detail page

## Testing Instructions

### Step 1: Apply Database Selectors
```bash
# Copy SQL file to container
docker cp add_booking_detail_selectors.sql gen_scraper-postgres-1:/tmp/

# Apply selectors
docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -f /tmp/add_booking_detail_selectors.sql
```

### Step 2: Restart Backend
```bash
docker-compose restart backend celery
```

### Step 3: Create Test Job
Via admin panel or API:
- Source: Booking.com
- Location: Kathmandu
- Max Results: 5
- Category: Hotels

### Step 4: Verify Results
```bash
docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c "
SELECT 
    name,
    amenities IS NOT NULL as has_amenities,
    review_scores IS NOT NULL as has_review_scores,
    checkin_time,
    checkout_time,
    languages,
    star_rating_detail
FROM cleaned_results 
WHERE source_id = 1 
ORDER BY created_at DESC 
LIMIT 5;
"
```

**Expected Results:**
- `has_amenities`: true for at least 3/5 records
- `has_review_scores`: true for at least 3/5 records
- `checkin_time`: "From 14:00 to 23:30" or similar
- `checkout_time`: "Until 12:00" or similar
- `languages`: "Hindi" or similar
- `star_rating_detail`: 3, 4, or 5

### Step 5: Check Logs
```bash
docker logs gen_scraper-celery-1 --tail 100 | grep "detail"
```

Look for:
- `scraper.starting_detail_extraction`
- `scraper.extracting_detail`
- `scraper.detail_data_merged`
- `scraper.detail_extraction_complete`

## Architecture Pattern (Google Maps Reference)

This implementation follows the exact pattern from `google_maps.py`:

1. **URL Collection Phase**
   - Scroll/paginate through search results
   - Extract detail page URLs from cards
   - Store URLs in list

2. **Detail Extraction Phase**
   - Visit each URL sequentially
   - Add delays between requests (3-6 seconds)
   - Extract enriched data
   - Merge with card data by URL matching

3. **Configuration**
   - Limit detail pages per job (default 10)
   - Configurable delays
   - CAPTCHA detection and graceful degradation

## Benefits

1. **Richer Data**: Amenities, review breakdowns, check-in times
2. **Better Matching**: More fields for fuzzy matching and deduplication
3. **User Value**: More complete hotel information
4. **Scalable**: Configurable limits prevent overload
5. **Resilient**: CAPTCHA detection, error handling, partial results

## Configuration Tuning

**For faster scraping (less data):**
```env
MAX_DETAIL_PAGES_PER_JOB=5
DETAIL_PAGE_DELAY_MIN=2000
DETAIL_PAGE_DELAY_MAX=4000
```

**For maximum data (slower):**
```env
MAX_DETAIL_PAGES_PER_JOB=20
DETAIL_PAGE_DELAY_MIN=4000
DETAIL_PAGE_DELAY_MAX=8000
```

**To disable detail scraping:**
```env
MAX_DETAIL_PAGES_PER_JOB=0
```

## Next Steps

1. ✅ Apply database selectors
2. ✅ Restart services
3. ⏳ Run test job
4. ⏳ Verify data quality
5. ⏳ Implement NepalYP detail scraping (same pattern)

## Notes

- **Phone numbers**: Not available on Booking.com public detail pages (company policy)
- **Coordinates**: Not extracted (Booking.com doesn't expose them publicly)
- **Images**: Only thumbnail extracted (full gallery would require additional requests)
- **Prices**: Already extracted from card data (detail page doesn't add more)

## Files Modified

1. `backend/scrapers/booking_com.py` - Added detail page scraping methods
2. `backend/config.py` - Added configuration variables
3. `.env` - Added configuration values
4. `add_booking_detail_selectors.sql` - New SQL file for selectors

## Files Created

1. `add_booking_detail_selectors.sql` - Database selectors
2. `BOOKING_DETAIL_SCRAPING_IMPLEMENTATION.md` - This documentation
