# Scraper Healing Migration Guide

## Overview

This guide explains how to migrate scrapers from hardcoded selectors to the database-driven selector system with automatic healing.

## Current Status

### ✅ Completed
- **Booking.com** - Fully migrated with reactive healing

### ⏳ Pending Migration
- Google Maps
- NepalYP
- DirectoryOfNepal
- Foodmandu
- Agoda
- Hostelworld
- OYO Rooms
- eSewa Hotels

## Migration Steps

### Step 1: Add Selectors to Database

For each scraper, add selector records to the `scraper_selectors` table:

```sql
-- Example for a new scraper
INSERT INTO scraper_selectors (source_id, field_name, selector, selector_type, is_active, verified_at)
VALUES
    (SOURCE_ID, 'name', '[data-testid="title"]', 'testid', true, NOW()),
    (SOURCE_ID, 'address', '.address-text', 'css', true, NOW()),
    (SOURCE_ID, 'phone', '[data-item-id*="phone"]', 'css', true, NOW()),
    (SOURCE_ID, 'rating', '.rating-score', 'css', true, NOW()),
    (SOURCE_ID, 'price', '.price-amount', 'css', true, NOW());
```

**Selector Types:**
- `testid` - data-testid attributes (most stable)
- `role` - ARIA roles (stable)
- `xpath` - XPath expressions (moderately stable)
- `css` - CSS selectors (least stable)

### Step 2: Add Field Hints to Source

Field hints are real example values used by the Inspector to find new selectors when healing:

```sql
UPDATE sources
SET field_hints = '{
    "name": "Hotel Example Name",
    "address": "123 Main Street, Kathmandu",
    "phone": "+977-1-234567",
    "rating": "4.5",
    "price": "$50"
}'::jsonb
WHERE id = SOURCE_ID;
```

**Best Practices for Field Hints:**
- Use real values from the actual website
- Make them specific enough to be unique
- Avoid generic values like "Hotel" or "Address"
- Update hints if website content changes

### Step 3: Modify Scraper Code

#### 3.1 Load Selectors in _scrape() Method

The `BaseScraper` already loads selectors automatically. Verify it's being called:

```python
async def _scrape(self, page, source: Source, db: Session, location: str, max_results: Optional[int] = None, category_id: Optional[int] = None) -> list[dict]:
    # Selectors are automatically loaded by BaseScraper.__init__()
    # Access them via self.selectors dictionary
    
    # Example: Get the 'name' selector
    name_selector_record = self.selectors.get('name')
    if name_selector_record:
        name_selector = name_selector_record.selector
```

#### 3.2 Replace Direct Extraction with Healing-Enabled Extraction

**OLD CODE (hardcoded selectors):**
```python
# Extract name
name = None
try:
    name_elem = await card.query_selector('h3.hotel-name')
    if name_elem:
        name = await name_elem.text_content()
        name = name.strip() if name else None
except Exception:
    pass
```

**NEW CODE (with healing):**
```python
# Extract name with healing
name = await self._extract_field_with_healing(
    card=card,          # The card/listing element
    page=page,          # The FULL PAGE object (not card!)
    source=source,      # Source model instance
    db=db,              # Database session
    field_name='name'   # Field name matching scraper_selectors.field_name
)
```

**Critical: Pass the correct arguments:**
- `card` - The card/listing element for extraction
- `page` - The **FULL PAGE** object (Inspector needs this to reload/search)
- `source` - The source record from database
- `db` - Database session for healing updates
- `field_name` - Must match the field_name in scraper_selectors table

#### 3.3 Update All Field Extractions

Apply the pattern to all fields:

```python
async def _extract_hotel_data(self, card, page, source, db) -> dict:
    """Extract hotel data from a card element."""
    
    # Extract all fields with healing
    name = await self._extract_field_with_healing(
        card=card, page=page, source=source, db=db, field_name='name'
    )
    
    address = await self._extract_field_with_healing(
        card=card, page=page, source=source, db=db, field_name='address'
    )
    
    phone = await self._extract_field_with_healing(
        card=card, page=page, source=source, db=db, field_name='phone'
    )
    
    rating = await self._extract_field_with_healing(
        card=card, page=page, source=source, db=db, field_name='rating'
    )
    
    price = await self._extract_field_with_healing(
        card=card, page=page, source=source, db=db, field_name='price'
    )
    
    return {
        "name": name,
        "address": address or f"{name}, {location}",
        "phone_primary": phone,
        "rating_overall": float(rating) if rating else None,
        "price_min": float(price) if price else None,
        # ... other fields
    }
```

#### 3.4 Update Call Sites

Ensure all calls to `_extract_hotel_data()` pass the required arguments:

```python
# OLD
hotel_data = await self._extract_hotel_data(card)

# NEW
hotel_data = await self._extract_hotel_data(card, page, source, db)
```

### Step 4: Test the Migration

#### 4.1 Test Normal Operation

Run a scrape job and verify:
- ✅ Data is extracted correctly
- ✅ No errors in logs
- ✅ Results saved to database

```bash
# Check results
docker-compose exec -T postgres psql -U scraper -d scraper_db -c "
SELECT name, address, phone_primary, rating_overall 
FROM cleaned_results 
WHERE job_id = 'YOUR_JOB_ID' 
LIMIT 5;
"
```

#### 4.2 Test Reactive Healing

Break a selector and verify healing works:

```sql
-- Break the name selector
UPDATE scraper_selectors 
SET selector = '[data-testid=BROKEN_FOR_TEST]' 
WHERE source_id = SOURCE_ID AND field_name = 'name';
```

Run a scrape job and check:
- ✅ `selector.extraction_failed` logged
- ✅ `inspector.attempting_reactive_heal` logged
- ✅ `inspector.skip_reload` logged (during active scrape)
- ✅ Healing attempted (confidence computed)
- ✅ Either healed successfully or failed gracefully
- ✅ Job completes without crashing

```bash
# Check healing logs
docker-compose logs worker | grep -E "selector\.|inspector\."

# Check heal log table
docker-compose exec -T postgres psql -U scraper -d scraper_db -c "
SELECT field_name, old_selector, new_selector, confidence, status 
FROM selector_heal_log 
WHERE source_id = SOURCE_ID 
ORDER BY created_at DESC 
LIMIT 5;
"
```

#### 4.3 Restore Selector After Test

```sql
UPDATE scraper_selectors 
SET selector = 'CORRECT_SELECTOR', 
    selector_type = 'CORRECT_TYPE'
WHERE source_id = SOURCE_ID AND field_name = 'name';
```

## Complete Example: Booking.com Migration

See `backend/scrapers/booking_com.py` for a complete working example.

### Key Changes Made:

1. **Selectors added to database** (via seed.py or migration)
2. **Field hints added to source** (real example values)
3. **_extract_hotel_data() signature updated:**
   ```python
   async def _extract_hotel_data(self, card, page, source, db) -> dict:
   ```

4. **All field extractions use healing:**
   ```python
   name = await self._extract_field_with_healing(
       card=card, page=page, source=source, db=db, field_name='name'
   )
   ```

5. **All call sites updated:**
   ```python
   hotel_data = await self._extract_hotel_data(card, page, source, db)
   ```

## Healing Behavior

### Reactive Healing (During Scrape)
- Triggered when selector fails during active scrape
- Inspector receives full page object
- **Skips page reload** if already on correct domain (NEW FIX!)
- Searches for new selector using field_hint
- Computes confidence score (0.0 - 1.0)
- If confidence ≥ 0.7: Updates selector, retries extraction
- If confidence < 0.7: Saves PENDING entry, returns None
- Job continues (never crashes)

### Proactive Healing (HTML Hash Change)
- Triggered when page HTML hash changes
- Runs for ALL fields of that source
- Reloads page to get fresh state
- Same confidence logic as reactive healing

### Graceful Degradation
- If healing fails, field value is None
- Job continues with partial data
- No crashes or exceptions
- PENDING entries queued for human review

## Common Pitfalls

### ❌ Passing Card Instead of Page to Inspector
```python
# WRONG - Inspector can't reload a card element
name = await self._extract_field_with_healing(
    card=card, page=card, ...  # ❌ page=card is wrong!
)
```

```python
# CORRECT - Inspector needs full page
name = await self._extract_field_with_healing(
    card=card, page=page, ...  # ✅ page is the full page object
)
```

### ❌ Missing Field Hints
Without field hints, Inspector can't find new selectors:
```sql
-- BAD - No field hints
UPDATE sources SET field_hints = NULL WHERE id = SOURCE_ID;

-- GOOD - Real example values
UPDATE sources SET field_hints = '{
    "name": "Actual Hotel Name From Website"
}'::jsonb WHERE id = SOURCE_ID;
```

### ❌ Generic Field Hints
Generic hints appear multiple times on page (low confidence):
```json
// BAD - Too generic
{"name": "Hotel", "address": "Address"}

// GOOD - Specific real values
{"name": "Radisson Hotel Kathmandu", "address": "Lazimpat, Kathmandu 44600"}
```

### ❌ Not Updating Call Sites
```python
# OLD call site - missing arguments
hotel_data = await self._extract_hotel_data(card)  # ❌ Missing page, source, db

# NEW call site - all arguments
hotel_data = await self._extract_hotel_data(card, page, source, db)  # ✅
```

## Migration Priority

Recommended order based on importance and complexity:

1. **High Priority (Simple Structure)**
   - ✅ Booking.com (DONE)
   - Agoda
   - Hostelworld
   - OYO Rooms

2. **Medium Priority (Moderate Complexity)**
   - NepalYP
   - DirectoryOfNepal
   - Foodmandu
   - eSewa Hotels

3. **Low Priority (Complex/Different Pattern)**
   - Google Maps (uses different extraction pattern)

## Benefits After Migration

### For Development
- ✅ No code redeployment when selectors break
- ✅ Automatic healing with confidence scoring
- ✅ Graceful degradation (no crashes)
- ✅ Audit trail in selector_heal_log

### For Operations
- ✅ Self-healing system reduces manual intervention
- ✅ PENDING entries queue low-confidence heals for review
- ✅ Proactive healing detects changes before failures
- ✅ Clear logging for debugging

### For Sales/Demo
> "When Booking.com updates their website, our system detects the change automatically within the next scrape. It scores potential new selectors by confidence (0-1.0). If confidence ≥ 0.7, it self-heals with zero human intervention. If confidence < 0.7, it queues the issue for a 5-minute human review instead of silently failing for weeks."

## Next Steps

1. ✅ Verify skip-reload fix works (test job pending)
2. Migrate Agoda scraper (similar to Booking.com)
3. Migrate Hostelworld scraper
4. Migrate OYO Rooms scraper
5. Build admin panel "Selector Health" page
6. Test proactive healing (HTML hash detection)
7. Document for production deployment

## Related Documents

- `REACTIVE_HEALING_SKIP_RELOAD_FIX.md` - Skip-reload fix details
- `HEALING_VERIFICATION_CHECKLIST.md` - Verification commands
- `SKIP_RELOAD_FIX_SUMMARY.md` - Executive summary
- `backend/scrapers/booking_com.py` - Complete working example
- `backend/scrapers/base_scraper.py` - Base implementation
- `backend/scrapers/inspector.py` - Healing logic
