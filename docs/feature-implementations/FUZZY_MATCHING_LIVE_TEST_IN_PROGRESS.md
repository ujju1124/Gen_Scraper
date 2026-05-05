# Fuzzy Matching - Live Test In Progress

**Date:** May 4, 2026  
**Job ID:** `38adced2-26e5-4548-9c0f-b2a9b61e2e0d`  
**Status:** Job running (scraping phase)

---

## Test Configuration

**Job Details:**
- **Category:** Hotels
- **Location:** Kathmandu
- **Max Results:** 50 per source
- **Sources Selected:**
  1. Booking.com (source_id=2)
  2. DirectoryOfNepal Hotels (source_id=12)
  3. Google Maps (source_id=30) - auto-appended

**Created via:** Playwright browser automation

---

## Scraping Progress

### Completed Sources

✅ **DirectoryOfNepal Hotels**
- Results: 50/50
- Status: Completed successfully
- Time: ~2 minutes

✅ **Booking.com**
- Results: 26/50 (all available)
- Status: Completed successfully  
- Time: ~2 minutes

🔄 **Google Maps** (In Progress)
- Status: Still scraping
- Progress: Extracting detail pages
- Expected: 50 results

---

## Expected Merger Behavior

Once all 3 sources complete scraping, the pipeline will run:

### 1. Cleaning Pipeline
- Normalizes data from all 3 sources
- Calculates dedup_key for each record
- Stores in `cleaned_results` table

### 2. Merging Pipeline (Two-Pass)

**Pass 1: Exact Matching**
- Groups records by identical dedup_key
- Merges records from different sources
- Expected: 0-5 exact matches (different sources rarely have identical names)

**Pass 2: Fuzzy Matching** ⭐ NEW
- Processes remaining non-merged records
- Uses 3 matching criteria:
  1. **Phone Match** - Same phone after normalization
  2. **Coordinate Match** - Within 50 meters
  3. **Name Match** - 80%+ similarity
- Expected: 10-20 fuzzy matches

---

## What to Look For in Logs

### Fuzzy Match Events

**Phone Match:**
```json
{
  "event": "merger.fuzzy_match_phone",
  "record_a_id": "uuid-1",
  "record_b_id": "uuid-2",
  "phone": "14411234"
}
```

**Coordinate Match:**
```json
{
  "event": "merger.fuzzy_match_coordinates",
  "record_a_id": "uuid-1",
  "record_b_id": "uuid-2",
  "distance_meters": 35.2
}
```

**Name Match:**
```json
{
  "event": "merger.fuzzy_match_name",
  "record_a_id": "uuid-1",
  "record_b_id": "uuid-2",
  "name_a": "Hotel Himalayan View",
  "name_b": "Hotel Himalayan Views",
  "similarity": 0.96
}
```

**Fuzzy Group Merged:**
```json
{
  "event": "merger.fuzzy_group_merged",
  "group_size": 2,
  "source_ids": [2, 12]
}
```

**Completion Summary:**
```json
{
  "event": "merger.complete",
  "job_id": "38adced2-26e5-4548-9c0f-b2a9b61e2e0d",
  "exact_merged_groups": 3,
  "fuzzy_merged_groups": 15,
  "total_merged_groups": 18,
  "total_records_processed": 126
}
```

---

## Commands to Monitor

### Check Worker Logs for Fuzzy Matching
```bash
docker-compose logs -f worker | grep "fuzzy\|merger.complete"
```

### Check Job Status
```bash
docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c \
"SELECT status FROM scrape_jobs WHERE id = '38adced2-26e5-4548-9c0f-b2a9b61e2e0d';"
```

### Check Merge Results
```bash
docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c \
"SELECT 
  COUNT(*) as total_records,
  COUNT(*) FILTER (WHERE is_duplicate = true) as duplicates,
  COUNT(*) FILTER (WHERE merged_from_sources IS NOT NULL) as merged_records
FROM cleaned_results
WHERE job_id = '38adced2-26e5-4548-9c0f-b2a9b61e2e0d';"
```

---

## Expected Results

### Before Fuzzy Matching (Baseline)
- Total records: ~126 (50 + 26 + 50)
- Exact merges: 0-5 groups
- Final unique records: ~121-126
- Merge rate: ~0-5%

### After Fuzzy Matching (Priority 3)
- Total records: ~126
- Exact merges: 0-5 groups
- Fuzzy merges: 10-20 groups
- Final unique records: ~106-116
- Merge rate: ~10-20%

**Why lower than 30-50% target?**
- Booking.com only returned 26 results (not 50)
- Different sources may have minimal overlap for Kathmandu hotels
- Google Maps uses different naming conventions (often in Nepali)

---

## Test Validation Criteria

✅ **Implementation Complete**
- 27/27 merger tests passing
- Phone normalization working
- Coordinate distance calculation working
- Name similarity matching working
- Two-pass merging implemented

🔄 **Live Test In Progress**
- Job created successfully via Playwright
- 3 sources scraping (2 complete, 1 in progress)
- Waiting for merger to run

⏳ **Pending Verification**
- Fuzzy match events in logs
- fuzzy_merged_groups > 0 in completion log
- Merge rate improvement vs baseline

---

## Next Steps

1. **Wait for job completion** (~5-10 more minutes for Google Maps)
2. **Check worker logs** for fuzzy matching events
3. **Query database** for merge statistics
4. **Document results** in completion report
5. **Proceed to Priority 4** (Hostelworld Selectors)

---

## Implementation Summary

**Files Modified:**
- `backend/scrapers/merger.py` (~155 lines added)
- `backend/tests/test_merger.py` (~200 lines added)

**Test Coverage:**
- 27/27 tests passing (100%)
- 13 new fuzzy matching tests
- Execution time: 90 seconds

**Features Implemented:**
- Phone normalization (Nepal format support)
- Haversine distance calculation
- Fuzzy name matching (80% threshold)
- Two-pass merging (exact + fuzzy)
- Comprehensive logging

---

**Status:** ✅ Implementation complete, live test in progress  
**Next Check:** Monitor logs for merger completion in ~10 minutes
