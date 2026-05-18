# 🚨 URGENT: Increase Docker Memory Limit

## Current Situation
- **Worker Memory**: 1.999GB/2GB (99.97% - **CRITICAL!**)
- **Your Laptop RAM**: 8GB total
- **Risk**: Jobs will crash if memory limit is hit

## ✅ Solution: Increase Docker Memory to 4GB (WSL2 Backend)

**Note**: Your Docker uses WSL2 backend, so memory is configured via `.wslconfig` file, not Docker Desktop UI.

### Step 1: Stop Docker Containers
```powershell
docker compose down
```

### Step 2: Create/Edit .wslconfig File

**Location**: `C:\Users\DELL\.wslconfig`

**Create the file with this content:**
```ini
[wsl2]
memory=4GB
processors=4
swap=2GB
localhostForwarding=true
```

**Why 4GB?**
- Your laptop has 8GB total
- Windows needs ~3-4GB
- Docker can safely use 4GB
- Leaves 4GB for Windows

### Step 3: Shutdown WSL2
```powershell
wsl --shutdown
```

Wait 5 seconds for WSL2 to fully shut down.

### Step 4: Restart Docker Desktop
1. Open **Docker Desktop** application
2. Wait for it to start (30-60 seconds)
3. Green indicator in bottom-left means ready

### Step 5: Restart Containers
```powershell
docker compose up -d
```

Wait 30 seconds for all services to start.

### Step 6: Re-queue Jobs
```powershell
docker exec gen_scraper-backend-1 python requeue_jobs.py
```

### Step 7: Verify Memory Increase
```powershell
docker stats --no-stream
```

**Expected Result:**
- Worker Memory: X MB / **4GB** (should be ~50% now)

---

## 🤖 Automated Script Available!

Run this script to do all steps automatically:
```powershell
.\fix-memory-issue.ps1
```

The script will:
1. ✅ Stop containers
2. ✅ Create .wslconfig file
3. ✅ Shutdown WSL2
4. ✅ Wait for Docker to restart
5. ✅ Start containers
6. ✅ Re-queue jobs
7. ✅ Verify memory

---

## Alternative: Manual docker-compose.yml Update

The `docker-compose.yml` is already updated with 4GB limit:
```yaml
worker:
  # ... other settings ...
  deploy:
    resources:
      limits:
        cpus: '2.0'
        memory: 4G  # ✅ Already set to 4GB
```

But WSL2 also needs to allow 4GB via `.wslconfig` file.

---

## After Increasing Memory

### Check Status:
```powershell
# Check memory usage
docker stats --no-stream

# Check records
docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c "SELECT COUNT(*) FROM cleaned_results;"

# Check jobs
docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c "SELECT status, COUNT(*) FROM scrape_jobs GROUP BY status;"
```

### Expected Improvements:
- ✅ Worker memory usage: ~50% instead of 99%
- ✅ No more crash risk
- ✅ Faster processing (less memory pressure)
- ✅ Can handle Google Maps better

---

## Job Distribution Analysis

**Current Queued Jobs:**
- Biratnagar: 23 jobs
- Butwal: 23 jobs
- Lalitpur: 23 jobs
- Dharan: 23 jobs
- Birgunj: 23 jobs
- Bhaktapur: 23 jobs
- Pokhara: 21 jobs
- Kathmandu: 2 jobs

**Total**: 161 jobs remaining

**Note**: Most jobs are for smaller cities, which should be faster than Kathmandu jobs.

---

## Why Memory is So High

### Google Maps Memory Usage:
- **Browser automation** (Playwright/Camoufox) uses lots of RAM
- **87 pages** for Pokhara hotels = 87 browser tabs worth of memory
- Each page loads images, maps, JavaScript
- Memory accumulates over time

### Solution Applied:
- Increasing Docker memory to 4GB
- This gives worker room to breathe
- Prevents crashes

---

## Timeline After Fix

With 4GB memory:
- **Safer operation**: No crash risk
- **Same speed**: ~64 records/hour
- **161 jobs remaining**: ~40-50 hours (2-3 days at 6-8 hours/day)

---

## Quick Commands Reference

### Stop Everything:
```powershell
docker compose down
```

### Start Everything:
```powershell
docker compose up -d
```

### Re-queue Jobs:
```powershell
docker exec gen_scraper-backend-1 python requeue_jobs.py
```

### Check Memory:
```powershell
docker stats --no-stream
```

### Check Progress:
```powershell
docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c "SELECT COUNT(*) FROM cleaned_results; SELECT status, COUNT(*) FROM scrape_jobs GROUP BY status;"
```

---

## 🎯 Action Plan

1. ✅ Stop Docker: `docker compose down`
2. ✅ Open Docker Desktop Settings
3. ✅ Increase Memory to 4GB
4. ✅ Apply & Restart
5. ✅ Start containers: `docker compose up -d`
6. ✅ Re-queue jobs: `docker exec gen_scraper-backend-1 python requeue_jobs.py`
7. ✅ Verify: `docker stats --no-stream`

**Do this now before the worker crashes!** 🚨
