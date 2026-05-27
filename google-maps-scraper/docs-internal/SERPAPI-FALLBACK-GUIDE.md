# SerpApi Fallback Implementation Guide

## Overview

The Google Maps scraper now includes SerpApi as an automatic fallback mechanism. When the primary Playwright-based scraper (gosom) fails or returns 0 results, the system automatically tries SerpApi to fetch the data.

## What Was Implemented

### 1. Backend Changes

#### Environment Configuration
- Added `SERPAPI_API_KEY` to `.env` file
- Added constant `EnvSerpApiKey` in `saas/constants.go`

#### SerpApi Package (`serpapi/`)
- `serpapi.go`: Client for making SerpApi requests
- `adapter.go`: Converts SerpApi results to `gmaps.Entry` format

#### Database Schema
- Added `scraper_source` column to `scrape_results` table
- Values: `"gosom"` (main scraper) or `"serpapi"` (fallback)
- Migration file: `migrations/20260414000000-add_scraper_source.sql`

#### Worker Fallback Logic (`rqueue/rqueue.go`)
- Modified `ScrapeWorker` to include fallback logic
- Added `trySerpApiFallback()` method
- Added `saveSerpApiResults()` method
- Fallback triggers when:
  - Main scraper returns 0 results
  - Main scraper encounters an error

#### API Updates
- Updated `JobStatus` struct to include `ScraperSource` field
- Modified `getResults()` to return scraper source
- Updated `GetJobStatus()` to include scraper source in response

### 2. Frontend Changes

#### Type Definitions (`frontend/src/lib/api.ts`)
- Added `scraper_source?: string` to `JobSummary` interface
- Added `scraper_source?: string` to `JobStatusResponse` interface

#### UI Display (`frontend/src/pages/JobDetails.tsx`)
- Added "Scraper Source" section in Job Information
- Displays badge:
  - 🔍 **Gosom Scraper** (blue) - Primary scraper
  - 🌐 **SerpApi Fallback** (green) - Fallback scraper

## How It Works

### Normal Flow (Main Scraper Success)
1. User submits a scrape job
2. Worker starts Playwright-based scraper (gosom)
3. Scraper returns results
4. Results saved with `scraper_source = 'gosom'`
5. Job completes successfully

### Fallback Flow (Main Scraper Fails)
1. User submits a scrape job
2. Worker starts Playwright-based scraper (gosom)
3. Scraper returns 0 results or encounters error
4. Worker logs: "main scraper returned 0 results, attempting SerpApi fallback"
5. Worker calls SerpApi with same search parameters
6. SerpApi returns results
7. Results converted to `gmaps.Entry` format
8. Results saved with `scraper_source = 'serpapi'`
9. Job completes successfully

### Both Scrapers Fail
1. Main scraper fails/returns 0 results
2. SerpApi fallback attempted
3. SerpApi also fails/returns 0 results
4. Job marked as failed with error message

## Setup Instructions

### 1. Run Database Migration

```powershell
# Stop the worker if running
# Run migration (this happens automatically on next startup)
# Or manually run:
.\start-dev.ps1
```

The migration will add the `scraper_source` column to existing `scrape_results` table.

### 2. Verify Environment Variables

Check `.env` file contains:
```
SERPAPI_API_KEY=c5318da2d53bb61c9836ee247aff77742838d1004021f898a2f50237ef73e4d9
```

### 3. Restart Services

```powershell
# Stop all services
.\stop-dev.ps1

# Start backend
.\start-dev.ps1

# Start worker (in new terminal)
.\start-worker.ps1

# Start frontend (in new terminal)
cd frontend
npm run dev
```

## Testing the Fallback

### Test 1: Normal Operation (Main Scraper Works)
1. Go to http://localhost:3000
2. Create a new job with a common search term:
   - Keyword: `hotels`
   - Location: `27.693444,85.281924` (Kathmandu)
   - Zoom: 14
   - Max Depth: 10
3. Wait for job to complete
4. Check job details - should show "🔍 Gosom Scraper"

### Test 2: Trigger Fallback (Intentional Failure)
To test the fallback, you can:

**Option A: Use obscure search term**
- Search for something very specific that might not load in Playwright
- Example: `very-specific-nonexistent-place-12345`

**Option B: Temporarily disable main scraper**
- Modify `rqueue/rqueue.go` to force 0 results
- Or set a very low timeout

**Option C: Check logs**
When fallback triggers, you'll see in worker logs:
```
INFO main scraper returned 0 results, attempting SerpApi fallback
INFO executing SerpApi search
INFO SerpApi search completed result_count=X
INFO saving serpapi results
INFO SerpApi fallback succeeded
```

### Test 3: Verify Frontend Display
1. After a job completes with SerpApi
2. Go to job details page
3. Look for "Scraper Source" section
4. Should show "🌐 SerpApi Fallback" badge in green

## Monitoring

### Check Scraper Usage
Query the database to see scraper usage:

```sql
-- Count by scraper source
SELECT scraper_source, COUNT(*) as count
FROM scrape_results
GROUP BY scraper_source;

-- Recent jobs with scraper source
SELECT job_id, keyword, result_count, scraper_source, created_at
FROM scrape_results
ORDER BY created_at DESC
LIMIT 10;
```

### Worker Logs
Watch for these log messages:
- `"main scraper returned 0 results, attempting SerpApi fallback"` - Fallback triggered
- `"executing SerpApi search"` - SerpApi request started
- `"SerpApi search completed"` - SerpApi returned results
- `"SerpApi fallback succeeded"` - Results saved successfully
- `"SerpApi fallback failed"` - Fallback encountered error

## Troubleshooting

### Fallback Not Triggering
- Check `SERPAPI_API_KEY` is set in `.env`
- Verify worker has been restarted after adding the key
- Check worker logs for "SERPAPI_API_KEY not configured" warning

### SerpApi Errors
- **401 Unauthorized**: Invalid API key
- **429 Rate Limit**: Too many requests (free tier: 100/month)
- **500 Server Error**: SerpApi service issue

### Database Errors
- Run migration if `scraper_source` column doesn't exist
- Check PostgreSQL is running: `docker ps`

### Frontend Not Showing Badge
- Clear browser cache
- Check API response includes `scraper_source` field
- Verify frontend is running latest code: `npm run dev`

## API Key Limits

SerpApi Free Tier:
- 100 searches per month
- After limit: API returns 429 error
- Fallback will fail, job marked as failed

To monitor usage:
- Check SerpApi dashboard: https://serpapi.com/dashboard
- Or count fallback jobs in database

## Future Improvements

1. **Metrics Dashboard**
   - Add fallback success rate to health endpoint
   - Track SerpApi usage vs main scraper

2. **Smart Fallback**
   - Skip fallback for known-bad queries
   - Cache SerpApi results to reduce API calls

3. **Multiple Fallbacks**
   - Add more fallback providers
   - Try fallbacks in sequence

4. **Cost Optimization**
   - Only use fallback for high-priority jobs
   - Implement retry logic before fallback

## Summary

The SerpApi fallback is now fully integrated:
- ✅ Automatic fallback when main scraper fails
- ✅ Database tracking of scraper source
- ✅ Frontend display of scraper used
- ✅ Comprehensive logging
- ✅ Error handling for both scrapers

Users will see improved reliability with minimal configuration required!
