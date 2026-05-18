# Reactive Healing Verification Checklist

## Test Job Details
- **Job ID**: `3d653606-e6a7-4e5f-9b5d-467a9692e603`
- **Celery Task ID**: `57c04b51-f680-491a-891c-4ae169fec360`
- **Source**: Booking.com (source_id=1)
- **Broken Selector**: `[data-testid=BROKEN_FOR_HEALING_TEST]` for field `name`
- **Expected Behavior**: Healing should trigger, skip reload, find new selector

## Verification Commands

### 1. Check Job Status
```bash
docker-compose exec -T postgres psql -U scraper -d scraper_db -c "
SELECT id, source_ids, status, error_message, started_at, completed_at 
FROM scrape_jobs 
WHERE id = '3d653606-e6a7-4e5f-9b5d-467a9692e603';
"
```

**Expected**: Status should be `DONE` (not `FAILED` or `RUNNING`)

### 2. Check Worker Logs for Healing Events
```bash
docker-compose logs worker | grep -E "selector\.|inspector\." | grep "3d653606"
```

**Expected Log Events**:
- `selector.extraction_failed` - Broken selector detected
- `selector.attempting_reactive_heal` - Healing triggered
- `inspector.skip_reload` - Reload skipped (page already loaded)
- `inspector.confidence_computed` - Confidence score calculated
- Either:
  - `selector.healed` - Healing succeeded (confidence ≥ 0.7)
  - `selector.heal_failed` - Healing failed (confidence < 0.7)

### 3. Check Selector Heal Log
```bash
docker-compose exec -T postgres psql -U scraper -d scraper_db -c "
SELECT 
    id,
    source_id,
    field_name,
    old_selector,
    new_selector,
    trigger,
    confidence,
    status,
    resolved_at,
    created_at
FROM selector_heal_log 
WHERE source_id = 1 AND field_name = 'name' 
ORDER BY created_at DESC 
LIMIT 1;
"
```

**Expected**:
- New entry should exist
- `trigger` = 'auto_reheal'
- `status` = 'RESOLVED' (if confidence ≥ 0.7) or 'PENDING' (if confidence < 0.7)
- `old_selector` = '[data-testid=BROKEN_FOR_HEALING_TEST]'
- `new_selector` = (new selector found by Inspector, if RESOLVED)
- `confidence` = (score between 0.0 and 1.0)

### 4. Check if Selector Was Updated
```bash
docker-compose exec -T postgres psql -U scraper -d scraper_db -c "
SELECT 
    field_name, 
    selector, 
    selector_type, 
    verified_at 
FROM scraper_selectors 
WHERE source_id = 1 AND field_name = 'name';
"
```

**Expected** (if healing succeeded):
- `selector` should be updated to new selector (not BROKEN_FOR_HEALING_TEST)
- `verified_at` should be recent timestamp
- `selector_type` should match the type found by Inspector

**Expected** (if healing failed):
- `selector` remains '[data-testid=BROKEN_FOR_HEALING_TEST]'
- Entry in selector_heal_log with status='PENDING'

### 5. Check Job Results
```bash
docker-compose exec -T postgres psql -U scraper -d scraper_db -c "
SELECT 
    COUNT(*) as total_results,
    COUNT(CASE WHEN name IS NOT NULL THEN 1 END) as results_with_name,
    COUNT(CASE WHEN name IS NULL THEN 1 END) as results_without_name
FROM cleaned_results 
WHERE job_id = '3d653606-e6a7-4e5f-9b5d-467a9692e603';
"
```

**Expected**:
- `total_results` = 3 (max_results setting)
- If healing succeeded: `results_with_name` = 3
- If healing failed: `results_without_name` = 3 (graceful degradation)

### 6. Verify No Timeout Errors
```bash
docker-compose logs worker | grep -E "timeout|TimeoutError" | grep "3d653606"
```

**Expected**: No timeout errors (this was the bug we fixed)

### 7. Check Specific Log for Skip-Reload
```bash
docker-compose logs worker | grep "inspector.skip_reload" | grep "3d653606"
```

**Expected**: Should see log entry indicating reload was skipped because page was already on correct domain

## Success Criteria

✅ **PASS** if:
1. Job status = DONE (not FAILED)
2. No timeout errors in logs
3. `inspector.skip_reload` event logged
4. Healing attempted (inspector.confidence_computed logged)
5. Either:
   - Healing succeeded: selector updated, results have names
   - Healing failed gracefully: PENDING entry in heal log, results have NULL names
6. Job completed without crashing

❌ **FAIL** if:
1. Job status = FAILED
2. Timeout errors in logs
3. Page reload attempted (no skip_reload log)
4. Job crashed or hung
5. No healing attempt logged

## Cleanup After Verification

### Restore Correct Selector
```bash
docker-compose exec -T postgres psql -U scraper -d scraper_db -c "
UPDATE scraper_selectors 
SET selector = '[data-testid=\"title\"]', 
    selector_type = 'testid',
    verified_at = NOW()
WHERE source_id = 1 AND field_name = 'name';
"
```

### Verify Restoration
```bash
docker-compose exec -T postgres psql -U scraper -d scraper_db -c "
SELECT field_name, selector, selector_type 
FROM scraper_selectors 
WHERE source_id = 1 AND field_name = 'name';
"
```

## Next Steps After Successful Verification

1. ✅ Verify skip-reload fix works
2. Apply healing pattern to other scrapers:
   - [ ] Google Maps (`backend/scrapers/google_maps.py`)
   - [ ] NepalYP (`backend/scrapers/nepalyp.py`)
   - [ ] DirectoryOfNepal (`backend/scrapers/directoryofnepal.py`)
   - [ ] Foodmandu (`backend/scrapers/foodmandu.py`)
   - [ ] Agoda (`backend/scrapers/agoda.py`)
   - [ ] Hostelworld (`backend/scrapers/hostelworld.py`)
   - [ ] OYO Rooms (`backend/scrapers/oyo_rooms.py`)
   - [ ] eSewa Hotels (`backend/scrapers/esewa_hotels.py`)

3. Test proactive healing (HTML hash change detection)
4. Build admin panel "Selector Health" page
5. Document the feature for sales/demo purposes

## Implementation Pattern for Other Scrapers

For each scraper, follow this pattern:

1. **Load selectors from DB** (already done in base_scraper)
2. **Use `_extract_field_with_healing()`** instead of direct `page.query_selector()`
3. **Pass correct arguments**:
   - `card` = the card/listing element
   - `page` = the full page object
   - `source` = the source record
   - `db` = database session
   - `field_name` = name of the field being extracted

Example:
```python
# OLD (direct extraction)
name_element = await card.query_selector(name_selector)
name = await name_element.text_content() if name_element else None

# NEW (with healing)
name = await self._extract_field_with_healing(
    card=card,
    page=page,
    source=source,
    db=db,
    field_name='name'
)
```

## Timeline

- **Fix Implemented**: 2026-05-12 12:10 UTC
- **Backend Rebuilt**: 2026-05-12 12:10 UTC
- **Test Job Created**: 2026-05-12 12:13 UTC
- **Verification Pending**: Waiting for worker to process queued jobs
- **Expected Completion**: ~15-20 minutes after Google Maps job finishes

## Related Documents

- `REACTIVE_HEALING_SKIP_RELOAD_FIX.md` - Detailed explanation of the fix
- `REACTIVE_HEALING_TEST_RESULTS.md` - Previous test showing timeout issue
- `CRITICAL_FIX_PAGE_VS_CARD.md` - Page vs card element fix
- `MERGE_RATE_AND_SELECTOR_ANALYSIS.md` - Context transfer summary
