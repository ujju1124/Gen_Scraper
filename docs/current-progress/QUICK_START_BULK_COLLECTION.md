# Quick Start: Bulk Data Collection

## 🚨 Current Status

Docker Desktop engine is not responding. You need to restart it first.

---

## Step-by-Step Instructions

### 1. Restart Docker Desktop

**Option A: Via System Tray**
- Right-click Docker Desktop icon (whale) in system tray
- Click "Restart Docker Desktop"
- Wait for it to fully start (icon stops animating)

**Option B: Via Task Manager**
- Open Task Manager (Ctrl+Shift+Esc)
- Find "Docker Desktop" process
- Right-click → End Task
- Start Docker Desktop from Start Menu

### 2. Start All Containers

```bash
cd C:\Users\DELL\Desktop\Gen_Scraper
docker-compose up -d
```

Wait 30 seconds, then verify:
```bash
docker ps
```

You should see 5 containers running:
- gen_scraper-postgres-1
- gen_scraper-redis-1
- gen_scraper-backend-1
- gen_scraper-worker-1
- gen_scraper-frontend-1

### 3. Check Existing Jobs

```bash
docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c "SELECT status, COUNT(*) FROM scrape_jobs GROUP BY status;"
```

### 4. Run Bulk Collection Script

```bash
docker exec gen_scraper-backend-1 python scripts/bulk_collect_simple.py
```

This will:
- ✅ Create ~100-120 scraping jobs
- ✅ Skip any duplicates automatically
- ✅ Cover 8 cities across Nepal
- ✅ Use 15+ categories and 20+ sources

**Expected output:**
```
🚀 BULK DATA COLLECTION SCRIPT (SIMPLE)
🔐 Logging in...
✅ Login successful

📍 Kathmandu (multiplier: 1.0)
  ✅ hotels / hostelworld / limit=200
  ✅ hotels / directoryofnepal_hotels / limit=200
  ...

📊 SUMMARY
✅ Created: 95 jobs
⚠️  Skipped: 20 jobs (duplicates)
❌ Failed: 0 jobs
```

### 5. Monitor Progress

**Check job status every 10-15 minutes:**
```bash
docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c "SELECT status, COUNT(*) FROM scrape_jobs GROUP BY status;"
```

**Check total records collected:**
```bash
docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c "SELECT COUNT(*) as total FROM cleaned_results;"
```

**Check records by city:**
```bash
docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c "SELECT city, COUNT(*) as records FROM cleaned_results GROUP BY city ORDER BY COUNT(*) DESC;"
```

**Watch worker logs (live):**
```bash
docker logs gen_scraper-worker-1 --tail 50 -f
```
Press Ctrl+C to stop watching.

---

## Expected Timeline

- **Job Creation**: 1-2 minutes
- **Processing**: 4-12 hours (depending on sources)
- **Total Records**: 5,000-8,000 expected

The Celery worker processes 2 jobs concurrently, so it will take several hours to complete all jobs.

---

## What to Do While It Runs

### Option 1: Let It Run Overnight
The worker will process all jobs automatically. Just check progress in the morning.

### Option 2: Monitor Periodically
Check every 30-60 minutes to see progress:
```bash
# Quick status check
docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c "SELECT status, COUNT(*) FROM scrape_jobs GROUP BY status; SELECT COUNT(*) as total_records FROM cleaned_results;"
```

### Option 3: Watch in Real-Time
Open the frontend and watch the admin panel:
- URL: http://localhost:5173
- Login: admin@example.com / admin123
- Go to Admin Panel → Scrape Jobs
- Refresh to see updates

---

## When All Jobs Complete

You'll see:
```
 status  | count 
---------+-------
 DONE    |   115
```

Then check your data:
```bash
# Total records
docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c "SELECT COUNT(*) FROM cleaned_results;"

# Records by city
docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c "SELECT city, COUNT(*) FROM cleaned_results GROUP BY city ORDER BY COUNT(*) DESC;"

# Records by category
docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c "SELECT c.name, COUNT(*) as records FROM cleaned_results cr JOIN categories c ON cr.category_id = c.id GROUP BY c.name ORDER BY COUNT(*) DESC;"
```

---

## Troubleshooting

### Docker Won't Start
- Restart your computer
- Check Windows Services → Docker Desktop Service is running
- Check WSL2 is working: `wsl --list --verbose`

### Containers Won't Start
```bash
# Check logs
docker-compose logs

# Restart specific service
docker-compose restart backend
docker-compose restart worker
```

### Jobs Stuck in RUNNING
```bash
# Restart worker
docker-compose restart worker

# Check worker logs
docker logs gen_scraper-worker-1 --tail 100
```

### No Data Being Collected
```bash
# Check worker is processing
docker logs gen_scraper-worker-1 --tail 50

# Check for errors
docker logs gen_scraper-worker-1 | grep -i error

# Restart everything
docker-compose restart
```

---

## Quick Commands Reference

```bash
# Start everything
docker-compose up -d

# Stop everything
docker-compose down

# Restart everything
docker-compose restart

# Check status
docker ps

# Job status
docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c "SELECT status, COUNT(*) FROM scrape_jobs GROUP BY status;"

# Total records
docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c "SELECT COUNT(*) FROM cleaned_results;"

# Worker logs
docker logs gen_scraper-worker-1 --tail 50 -f

# Backend logs
docker logs gen_scraper-backend-1 --tail 50

# Run bulk collection
docker exec gen_scraper-backend-1 python scripts/bulk_collect_simple.py
```

---

## Summary

1. ✅ Restart Docker Desktop
2. ✅ Start containers: `docker-compose up -d`
3. ✅ Run script: `docker exec gen_scraper-backend-1 python scripts/bulk_collect_simple.py`
4. ✅ Monitor: Check job status every 10-15 minutes
5. ✅ Wait: 4-12 hours for completion
6. ✅ Verify: Check total records collected

**That's it!** The system will automatically scrape all data in the background.
