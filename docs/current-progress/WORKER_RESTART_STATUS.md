# Worker Restart and Recovery Status

**Date**: May 5, 2026, 3:55 PM  
**Issue**: Jobs stuck at 2,489 records with Google Maps timeout errors

## Problem Identified

The system appeared "stuck" because 3 jobs were experiencing continuous timeout errors on Google Maps detail pages:
- Each Google Maps detail page was timing out after 30 seconds
- The worker kept trying page after page, but all were timing out
- No new records were being saved (0 records in last 10 minutes)
- Google Maps was likely detecting bot activity and slowing/blocking responses

## Actions Taken

### 1. Worker Restart
```bash
docker compose restart worker
```
- Cleared the stuck browser sessions
- Reset worker process
- Allowed system to pick up fresh jobs from queue

### 2. Reset Stuck Jobs
```sql
UPDATE scrape_jobs SET status = 'QUEUED' WHERE status = 'RUNNING';
```
- Reset 4 jobs from RUNNING back to QUEUED
- These jobs will be retried later
- Prevents them from blocking the queue

## Current Status

### Job Distribution
- **DONE**: 26 jobs completed
- **QUEUED**: 188 jobs waiting
- **RUNNING**: 0 (worker processing but not stuck)
- **Total**: 214 jobs

### Records Collected
- **Total**: 2,489 records
- **Top Cities**:
  - Kathmandu: 1,387 records
  - Chitwan: 293 records
  - Sunsari: 158 records
  - Rupandehi: 118 records
  - Lalitpur: 69 records

### Worker Activity
Worker is now actively processing jobs:
- DirectoryOfNepal scraper: Working well (fetching pages 11-25 of 200)
- Google Maps scraper: Running in parallel (collecting URLs)
- No timeout errors currently
- System is stable

## Expected Behavior

### Normal Operation
- Worker processes 1 job at a time (CELERY_CONCURRENCY=1)
- Each job may take 10-30 minutes depending on:
  - Number of results to collect (max_results)
  - Source response times
  - Google Maps timeout issues
- New records appear in database as jobs complete

### Google Maps Timeout Issue
- **Cause**: Google Maps detects bot activity and slows responses
- **Impact**: Some detail pages timeout after 30 seconds
- **Behavior**: Scraper continues to next page, logs warning
- **Result**: Partial data collected (list data without full details)

### When to Worry
- No new records for **1+ hours** = likely stuck
- All jobs show RUNNING for **30+ minutes** = worker may be frozen
- Docker containers showing "Exited" status = crash

### When NOT to Worry
- Jobs taking 15-30 minutes = normal for large result sets
- Timeout warnings in logs = expected for Google Maps
- Slow progress = normal with 1 concurrent worker

## Monitoring Commands

### Check Job Status
```bash
docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c \
  "SELECT status, COUNT(*) as count FROM scrape_jobs GROUP BY status ORDER BY status;"
```

### Check Record Count
```bash
docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c \
  "SELECT COUNT(*) as total_records FROM cleaned_results;"
```

### Check Recent Records (last 10 minutes)
```bash
docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c \
  "SELECT COUNT(*) FROM cleaned_results WHERE created_at > NOW() - INTERVAL '10 minutes';"
```

### Check Worker Logs
```bash
docker logs gen_scraper-worker-1 --tail 30
```

### Check Container Status
```bash
docker compose ps
```

## Recovery Steps (If Stuck Again)

### Step 1: Verify It's Actually Stuck
```bash
# Check if new records added in last 10 minutes
docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c \
  "SELECT COUNT(*) FROM cleaned_results WHERE created_at > NOW() - INTERVAL '10 minutes';"

# If result is 0, check worker logs
docker logs gen_scraper-worker-1 --tail 50
```

### Step 2: Restart Worker
```bash
docker compose restart worker
```

### Step 3: Reset Stuck Jobs
```bash
docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c \
  "UPDATE scrape_jobs SET status = 'QUEUED' WHERE status = 'RUNNING';"
```

### Step 4: Verify Recovery
```bash
# Wait 2-3 minutes, then check logs
docker logs gen_scraper-worker-1 --tail 30

# Should see active scraping logs like:
# - "directoryofnepal.fetching_detail"
# - "google_maps.scroll_iteration"
# - "orchestrator.scraper_starting"
```

## Long-Term Solutions

### Option 1: Increase Google Maps Timeout
Edit `backend/scrapers/google_maps.py`:
```python
# Line 265: Change timeout from 30000 to 60000
await page.goto(url, wait_until="domcontentloaded", timeout=60000)
```

### Option 2: Add Retry Logic
Add exponential backoff for failed pages:
```python
max_retries = 3
for retry in range(max_retries):
    try:
        await page.goto(url, timeout=30000)
        break
    except TimeoutError:
        if retry < max_retries - 1:
            await page.wait_for_timeout(5000 * (retry + 1))
        else:
            logger.warning("google_maps.max_retries_exceeded")
```

### Option 3: Skip Google Maps for Problematic Categories
Modify orchestrator to skip Google Maps for categories that consistently timeout:
```python
SKIP_GOOGLE_MAPS_CATEGORIES = ['hospitals', 'clinics']
if category_id not in SKIP_GOOGLE_MAPS_CATEGORIES:
    sources.append(google_maps_source)
```

## Estimated Completion Time

- **Jobs Remaining**: 188
- **Average Time per Job**: 15-20 minutes
- **Estimated Time**: 47-63 hours (2-3 days)
- **Completion Date**: May 7-8, 2026

**Important**: Keep computer ON with sleep mode disabled for continuous operation.

## Next Steps

1. ✅ Worker restarted and processing jobs
2. ✅ Stuck jobs reset to QUEUED
3. ⏳ Monitor progress every 1-2 hours
4. ⏳ Check for new records being added
5. ⏳ Wait for all 214 jobs to complete

**Status**: System is now working properly. No action needed unless stuck again for 1+ hour.
