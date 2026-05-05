# Fuzzy Matching - Live Testing Guide

## How to Test Fuzzy Matching in Production

### Step 1: Create a Multi-Source Job

**Via Frontend UI:**
1. Go to "Create New Job"
2. **Location:** Kathmandu
3. **Category:** Hotels
4. **Sources:** Select multiple sources:
   - ✅ nepalyp_hotels
   - ✅ directoryofnepal_hotels
   - ✅ google_maps
5. **Max Results:** 50 (per source)
6. Click "Start Job"

### Step 2: Monitor Worker Logs

Open a terminal and run:
```bash
docker-compose logs -f worker
```

### Step 3: Look for Fuzzy Match Events

You should see log entries like these:

#### Phone Match Example
```json
{
  "event": "merger.fuzzy_match_phone",
  "record_a_id": "abc-123",
  "record_b_id": "def-456",
  "phone": "14411234",
  "timestamp": "2026-05-04T10:30:00Z",
  "level": "debug"
}
```

#### Coordinate Match Example
```json
{
  "event": "merger.fuzzy_match_coordinates",
  "record_a_id": "abc-123",
  "record_b_id": "ghi-789",
  "distance_meters": 35.2,
  "timestamp": "2026-05-04T10:30:01Z",
  "level": "debug"
}
```

#### Name Match Example
```json
{
  "event": "merger.fuzzy_match_name",
  "record_a_id": "abc-123",
  "record_b_id": "jkl-012",
  "name_a": "Hotel Himalayan View",
  "name_b": "Hotel Himalayan Views",
  "similarity": 0.96,
  "timestamp": "2026-05-04T10:30:02Z",
  "level": "debug"
}
```

#### Fuzzy Group Merged
```json
{
  "event": "merger.fuzzy_group_merged",
  "group_size": 2,
  "source_ids": [2, 12],
  "timestamp": "2026-05-04T10:30:03Z",
  "level": "info"
}
```

#### Completion Summary
```json
{
  "event": "merger.complete",
  "job_id": "abc-123-def-456",
  "exact_merged_groups": 8,
  "fuzzy_merged_groups": 3,
  "total_merged_groups": 11,
  "total_records_processed": 150,
  "timestamp": "2026-05-04T10:30:10Z",
  "level": "info"
}
```

### Step 4: Check Results in Database

```bash
docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c "
SELECT 
  COUNT(*) as total_records,
  COUNT(*) FILTER (WHERE is_duplicate = true) as duplicates,
  COUNT(*) FILTER (WHERE merged_from_sources IS NOT NULL) as merged_records,
  COUNT(DISTINCT CASE WHEN merged_from_sources IS NOT NULL THEN id END) as canonical_records
FROM cleaned_results
WHERE job_id = 'YOUR_JOB_ID_HERE';
"
```

### Step 5: Verify Merge Quality

Check a merged record to see fuzzy matching in action:

```bash
docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c "
SELECT 
  name,
  phone_primary,
  latitude,
  longitude,
  merged_from_sources,
  confidence_score,
  data_completeness
FROM cleaned_results
WHERE job_id = 'YOUR_JOB_ID_HERE'
  AND merged_from_sources IS NOT NULL
LIMIT 5;
"
```

---

## What to Look For

### Good Signs ✅

1. **Fuzzy match events in logs**
   - Shows fuzzy matching is working

2. **fuzzy_merged_groups > 0**
   - Shows records are being matched beyond exact dedup_key

3. **Higher data_completeness scores**
   - Merged records have more fields filled

4. **Reasonable merge rate**
   - 30-50% of records merged (vs 5% before)

### Red Flags 🚩

1. **No fuzzy match events**
   - Fuzzy matching may not be running
   - Check if records have different dedup_keys

2. **fuzzy_merged_groups = 0**
   - Records may be too dissimilar
   - Try a different location/category with more overlap

3. **Too many merges (>80%)**
   - May indicate false positives
   - Check merged records manually

---

## Example: Expected Results

### Job Configuration
- Location: Kathmandu
- Category: Hotels
- Sources: nepalyp_hotels (20 results) + directoryofnepal_hotels (15 results) + google_maps (50 results)
- Total raw results: 85

### Expected Outcome

**Pass 1 (Exact Matching):**
- Exact matches: 5-10 groups
- Records merged: 10-20

**Pass 2 (Fuzzy Matching):**
- Fuzzy matches: 3-8 groups
- Records merged: 6-16

**Final Result:**
- Total merged groups: 8-18
- Final unique records: 67-77 (vs 85 raw)
- Merge rate: 20-30%

---

## Troubleshooting

### No Fuzzy Matches Found

**Possible Causes:**
1. All records already merged in exact pass
2. Records are too dissimilar (different names, no phones, far apart)
3. Records are from same source (safety check prevents merge)

**Solutions:**
- Try a different location with more data overlap
- Check if sources have phone numbers and coordinates
- Verify sources are actually returning different records

### Too Many False Positives

**Possible Causes:**
1. Common business names (e.g., "Hotel Nepal")
2. Coordinate clustering in same area
3. Phone number reuse

**Solutions:**
- Check merged records manually
- Consider raising name similarity threshold (80% → 85%)
- Consider reducing coordinate radius (50m → 30m)

### Performance Issues

**Possible Causes:**
1. Too many records (>10,000)
2. Nested loop in fuzzy pass is slow

**Solutions:**
- Reduce max_results per source
- Run job during off-peak hours
- Consider adding indexing (future optimization)

---

## Quick Test Commands

### Count Fuzzy Matches in Logs
```bash
docker-compose logs worker | grep "fuzzy_match" | wc -l
```

### Count Fuzzy Groups Merged
```bash
docker-compose logs worker | grep "fuzzy_group_merged" | wc -l
```

### Get Latest Job Stats
```bash
docker-compose logs worker | grep "merger.complete" | tail -1
```

### Check Merge Rate
```bash
docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c "
SELECT 
  COUNT(*) as total,
  COUNT(*) FILTER (WHERE merged_from_sources IS NOT NULL) as merged,
  ROUND(100.0 * COUNT(*) FILTER (WHERE merged_from_sources IS NOT NULL) / COUNT(*), 1) as merge_rate_pct
FROM cleaned_results
WHERE job_id = 'YOUR_JOB_ID_HERE';
"
```

---

## Success Criteria

✅ Fuzzy match events appear in logs  
✅ fuzzy_merged_groups > 0  
✅ Merge rate improves from 5% to 20-50%  
✅ No obvious false positives in merged records  
✅ data_completeness scores increase after merge  

---

**Ready to test!** Create a multi-source job and watch the logs for fuzzy matching in action.
