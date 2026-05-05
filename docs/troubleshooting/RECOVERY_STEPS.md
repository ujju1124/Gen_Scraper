# Docker Reinstall Recovery Guide

**Situation:** Docker Desktop reinstalled, all containers and images gone  
**Impact:** Lost 1,491 records from Batch 1 (Hotels job completed with 240 records)  
**Solution:** Rebuild everything from scratch

---

## Step 1: Rebuild All Containers

This will rebuild all images and start all containers:

```bash
docker-compose up -d --build
```

**What this does:**
- Builds backend image (Python + dependencies)
- Builds frontend image (React + Vite)
- Pulls postgres, redis, rabbitmq images
- Creates and starts all 6 containers:
  - postgres (database)
  - redis (caching)
  - rabbitmq (message queue)
  - backend (FastAPI)
  - worker (Celery)
  - frontend (React)

**Expected time:** 5-10 minutes (first build is slow)

---

## Step 2: Wait for Containers to Start

Check container status:
```bash
docker-compose ps
```

**Expected output:**
```
NAME                    STATUS
gen_scraper-backend-1   Up
gen_scraper-frontend-1  Up
gen_scraper-postgres-1  Up
gen_scraper-rabbitmq-1  Up
gen_scraper-redis-1     Up
gen_scraper-worker-1    Up
```

All should show "Up" status.

---

## Step 3: Initialize Database

The database is empty. Run migrations and seed data:

```bash
# Run Alembic migrations
docker exec gen_scraper-backend-1 alembic upgrade head

# Seed categories, sources, and admin user
docker exec gen_scraper-backend-1 python seed.py
```

**Expected output:**
- Migrations: "Running upgrade ... -> ..."
- Seed: "✓ Seeded X categories", "✓ Seeded X sources", "✓ Created admin user"

---

## Step 4: Verify Everything Works

### 4.1 Check backend health:
```bash
curl http://localhost:8000/health
```
Expected: `{"status":"healthy"}`

### 4.2 Check frontend:
Open browser: http://localhost:5173

### 4.3 Login:
- Email: admin@example.com
- Password: admin123

### 4.4 Check database:
```bash
docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c "SELECT COUNT(*) FROM categories;"
docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c "SELECT COUNT(*) FROM sources WHERE is_active=true;"
```

Expected:
- Categories: ~10-15
- Active sources: ~20-25

---

## Step 5: Resume Batch Jobs

**All previous data is lost.** Start fresh from Batch 1:

```bash
python bulk_job_creator.py --batch 1
```

This will create 5 jobs for Kathmandu:
1. Hotels (200 limit)
2. Restaurants (200 limit)
3. Hospitals (200 limit)
4. Banks (100 limit)
5. Schools (100 limit)

Monitor with:
```bash
python monitor_batch1.py
```

---

## Troubleshooting

### If build fails:
```bash
# Clean everything and rebuild
docker-compose down -v
docker system prune -a -f
docker-compose up -d --build
```

### If postgres won't start:
```bash
# Check logs
docker logs gen_scraper-postgres-1

# Restart
docker-compose restart postgres
```

### If worker won't start:
```bash
# Check logs
docker logs gen_scraper-worker-1

# Restart
docker-compose restart worker
```

### If frontend shows connection error:
```bash
# Check backend is running
docker logs gen_scraper-backend-1 --tail 50

# Restart both
docker-compose restart backend frontend
```

---

## What Was Lost

**Data:**
- 1,491 total records
- 1,017 Kathmandu records
- 240 hotels from completed job
- All other scraped data

**Not Lost (still in code):**
- All source configurations
- All scraper implementations
- All database schema
- All tests
- All automation scripts

**Recovery time:** ~15-20 minutes to rebuild + ~30-60 minutes to re-run Batch 1

---

## Prevention for Future

### Option 1: Docker Volume Backup (Recommended)
Before major operations, backup postgres volume:
```bash
docker run --rm -v gen_scraper_postgres_data:/data -v ${PWD}:/backup ubuntu tar czf /backup/postgres_backup.tar.gz /data
```

Restore:
```bash
docker run --rm -v gen_scraper_postgres_data:/data -v ${PWD}:/backup ubuntu tar xzf /backup/postgres_backup.tar.gz -C /
```

### Option 2: Database Dump
```bash
# Backup
docker exec gen_scraper-postgres-1 pg_dump -U scraper scraper_db > backup.sql

# Restore
docker exec -i gen_scraper-postgres-1 psql -U scraper -d scraper_db < backup.sql
```

### Option 3: Export to CSV
Use the export feature in the admin panel to download data as CSV before risky operations.

---

## Next Steps

1. Run: `docker-compose up -d --build`
2. Wait 5-10 minutes for build to complete
3. Run: `docker exec gen_scraper-backend-1 alembic upgrade head`
4. Run: `docker exec gen_scraper-backend-1 python seed.py`
5. Verify: http://localhost:5173
6. Resume: `python bulk_job_creator.py --batch 1`

---

**Status:** Ready to rebuild - all code is intact, just need to recreate containers and database
