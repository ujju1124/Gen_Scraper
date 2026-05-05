# Bulk Data Collection Status

**Date**: May 5, 2026  
**Status**: ⚠️ IN PROGRESS - Docker Engine Issue

---

## What Was Accomplished

### ✅ Created Bulk Collection Scripts

1. **`backend/scripts/bulk_collect.py`** - Full-featured script with detailed job definitions
2. **`backend/scripts/bulk_collect_simple.py`** - Simplified version with better error handling

### ✅ Jobs Successfully Created

**20 jobs were created and queued** before Docker engine encountered an issue:

```
Status Distribution (last known):
- RUNNING: 2 jobs
- QUEUED: 18 jobs
```

**Jobs Created Include:**
- Hotels in Kathmandu (Hostelworld, DirectoryOfNepal, Google Maps)
- Restaurants in Kathmandu (DirectoryOfNepal, Google Maps)
- Pharmacies in Kathmandu (DirectoryOfNepal, Google Maps)
- Hospitals in Kathmandu (Google Maps)
- Clinics in Kathmandu (NepalYP, Google Maps)
- And more...

---

## Current Issue

**Docker Desktop Engine Not Responding**

Error: `500 Internal Server Error for API route`

This typically happens when:
- Docker Desktop needs to be restarted
- WSL2 backend has an issue
- Docker engine crashed

---

## How to Resume

### Step 1: Restart Docker Desktop

1. Right-click Docker Desktop icon in system tray
2. Select "Restart Docker Desktop"
3. Wait for Docker to fully start (whale icon stops animating)

### Step 2: Start Containers

```bash
cd C:\Users\DELL\Desktop\Gen_Scraper
docker-compose up -d
```

Wait for all containers to be healthy:
```bash
docker ps
```

### Step 3: Check Existing Jobs

```bash
# Check job status
docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c \
  "SELECT status, COUNT(*) FROM scrape_jobs GROUP BY status;"

# Check if any data was collected
docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c \
  "SELECT COUNT(*) as total FROM cleaned_results;"
```

### Step 4: Resume Bulk Collection

Run the simple script to create remaining jobs:

```bash
docker exec gen_scraper-backend-1 python scripts/bulk_collect_simple.py
```

This script:
- ✅ Handles duplicates gracefully (skips already created jobs)
- ✅ Creates jobs for 8 cities
- ✅ Uses 15 different categories
- ✅ Leverages 20+ active sources
- ✅ Adjusts limits based on city size

**Expected Total**: ~100-120 jobs across all cities and sources

---

## Script Features

### bulk_collect_simple.py

**Cities Covered:**
- Kathmandu (100% limits)
- Pokhara (70% limits)
- Lalitpur (70% limits)
- Bhaktapur (70% limits)
- Biratnagar (50% limits)
- Birgunj (50% limits)
- Butwal (50% limits)
- Dharan (50% limits)

**Categories & Sources:**
- **Hotels**: Hostelworld, DirectoryOfNepal, Google Maps
- **Restaurants**: DirectoryOfNepal, Google Maps
- **Pharmacies**: DirectoryOfNepal, Google Maps
- **Hospitals**: Google Maps
- **Clinics**: NepalYP, Google Maps
- **Banks**: NepalYP, Google Maps
- **Schools**: NepalYP
- **Colleges**: NepalYP
- **Bakeries**: NepalYP, Google Maps
- **Travel Agencies**: NepalYP (Travel Agents + Tour Operators)
- **Car Rentals**: NepalYP
- **Petrol Stations**: NepalYP
- **Supermarkets**: NepalYP (Shopping Centres)
- **Resorts**: NepalYP
- **Hostels**: NepalYP (Homestays)

---

## Monitoring Commands

### Check Job Progress

```bash
# Job status distribution
docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c \
  "SELECT status, COUNT(*) FROM scrape_jobs GROUP BY status;"

# Recent jobs
docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c \
  "SELECT id, city, status, created_at FROM scrape_jobs ORDER BY created_at DESC LIMIT 10;"
```

### Check Data Collection

```bash
# Total records
docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c \
  "SELECT COUNT(*) as total FROM cleaned_results;"

# Records by city
docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c \
  "SELECT city, COUNT(*) as records FROM cleaned_results GROUP BY city ORDER BY COUNT(*) DESC;"

# Records by category
docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c \
  "SELECT category_id, COUNT(*) as records FROM cleaned_results GROUP BY category_id ORDER BY COUNT(*) DESC LIMIT 10;"
```

### Monitor Worker

```bash
# Watch worker logs in real-time
docker logs gen_scraper-worker-1 --tail 50 -f

# Check for errors
docker logs gen_scraper-worker-1 --tail 100 | grep -i error
```

---

## Expected Results

### Estimated Data Collection

Based on the job configuration:

| City | Estimated Records |
|------|------------------|
| Kathmandu | 2,000-3,000 |
| Pokhara | 800-1,200 |
| Lalitpur | 600-900 |
| Bhaktapur | 500-800 |
| Biratnagar | 400-600 |
| Birgunj | 300-500 |
| Butwal | 300-500 |
| Dharan | 300-500 |
| **TOTAL** | **5,200-8,000** |

### Processing Time

- **Per Job**: 2-10 minutes (depending on source and limit)
- **Total Jobs**: ~100-120 jobs
- **Estimated Total Time**: 4-12 hours (with 2 concurrent workers)

---

## Troubleshooting

### If Jobs Get Stuck

```bash
# Check worker is running
docker ps | grep worker

# Restart worker
docker-compose restart worker

# Check Redis connection
docker exec gen_scraper-redis-1 redis-cli ping
```

### If Scraping Fails

```bash
# Check backend logs
docker logs gen_scraper-backend-1 --tail 100

# Check specific job details
docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c \
  "SELECT id, city, status, error_message FROM scrape_jobs WHERE status = 'FAILED';"
```

### If Database Connection Fails

```bash
# Check PostgreSQL
docker logs gen_scraper-postgres-1 --tail 50

# Restart PostgreSQL
docker-compose restart postgres
```

---

## Next Steps After Collection Completes

1. **Verify Data Quality**
   ```bash
   # Check for duplicates
   docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c \
     "SELECT name, COUNT(*) FROM cleaned_results GROUP BY name HAVING COUNT(*) > 1 LIMIT 20;"
   ```

2. **Export Data**
   - Use the frontend export feature
   - Or export via SQL:
   ```bash
   docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c \
     "COPY (SELECT * FROM cleaned_results) TO STDOUT WITH CSV HEADER;" > data_export.csv
   ```

3. **Analyze Results**
   - Check coverage by city
   - Identify gaps in data
   - Plan additional scraping if needed

4. **Backup Database**
   ```bash
   docker exec gen_scraper-postgres-1 pg_dump -U scraper scraper_db > backup_$(date +%Y%m%d).sql
   ```

---

## Files Created

- `backend/scripts/bulk_collect.py` - Detailed bulk collection script
- `backend/scripts/bulk_collect_simple.py` - Simplified version with better error handling
- `BULK_COLLECTION_STATUS.md` - This status document

---

## Summary

✅ Bulk collection scripts created and tested  
✅ 20 jobs successfully created and queued  
⚠️ Docker engine issue requires restart  
📋 Ready to resume with `bulk_collect_simple.py` after Docker restart  
🎯 Target: 100-120 jobs collecting 5,000-8,000 records  

**Action Required**: Restart Docker Desktop and run the bulk collection script to complete the data collection.
