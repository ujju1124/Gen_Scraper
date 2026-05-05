# Docker Recovery - Quick Start Guide

**Status:** Docker reinstalled, engine running, all containers/images gone

**Goal:** Configure E: drive → Rebuild containers → Restore system

---

## ⚠️ CRITICAL: Do Step 1 First!

If you skip Step 1, you'll fill up C: drive again and be back to square one.

---

## Step 1: Configure Docker to Use E: Drive

### Option A: Via Docker Desktop Settings (Easiest)

1. **Open Docker Desktop**
2. Click **Settings** (gear icon ⚙️)
3. Go to **Resources** → **Advanced**
4. Find **"Disk image location"**
5. Change to: `E:\Docker`
6. Click **Apply & Restart**
7. Wait 2-3 minutes for Docker to restart

### Option B: Via WSL2 (If Option A doesn't work)

Run these commands in **PowerShell as Administrator**:

```powershell
# Stop Docker Desktop (right-click tray icon → Quit)

# Shutdown WSL
wsl --shutdown

# Create E: drive directory
New-Item -ItemType Directory -Path "E:\Docker\wsl" -Force

# Export current WSL distributions
wsl --export docker-desktop "E:\Docker\wsl\docker-desktop.tar"
wsl --export docker-desktop-data "E:\Docker\wsl\docker-desktop-data.tar"

# Unregister old distributions
wsl --unregister docker-desktop
wsl --unregister docker-desktop-data

# Import to E: drive
wsl --import docker-desktop "E:\Docker\wsl\docker-desktop" "E:\Docker\wsl\docker-desktop.tar" --version 2
wsl --import docker-desktop-data "E:\Docker\wsl\docker-desktop-data" "E:\Docker\wsl\docker-desktop-data.tar" --version 2

# Start Docker Desktop
```

### Verify E: Drive Configuration

```bash
# Check Docker is running
docker version

# Check WSL location (if using WSL2)
wsl --list -v
```

**Expected:** Should show docker-desktop and docker-desktop-data

---

## Step 2: Verify E: Drive Has Space

```powershell
Get-PSDrive E
```

**Need:** At least 15 GB free

**Current E: drive status:**
- Used: 1.5 GB
- Free: 260 GB ✅ (Plenty of space!)

---

## Step 3: Navigate to Project

```bash
cd C:/Users/DELL/Desktop/Gen_Scraper
```

---

## Step 4: Check docker-compose.yml Exists

```bash
ls docker-compose.yml
```

**Expected:** File should exist

---

## Step 5: Rebuild All Containers

```bash
docker-compose up -d --build
```

**This will:**
1. Pull base images (postgres, redis, rabbitmq) - ~5 min
2. Build backend image - ~5 min
3. Build frontend image - ~2 min
4. Start all 6 containers - ~1 min

**Total time:** 10-15 minutes

### Monitor Progress

Open a second terminal and run:

```bash
docker-compose logs -f
```

**Watch for:**
- ✅ "Pulling" messages (downloading images)
- ✅ "Building" messages (building custom images)
- ✅ "Created" messages (containers starting)
- ❌ Any "ERROR" messages

---

## Step 6: Wait for All Containers to Start

```bash
docker-compose ps
```

**Expected output:**
```
NAME                    STATUS
gen_scraper-backend-1   Up
gen_scraper-frontend-1  Up
gen_scraper-postgres-1  Up (healthy)
gen_scraper-rabbitmq-1  Up
gen_scraper-redis-1     Up
gen_scraper-worker-1    Up
```

**If any show "Restarting" or "Exited":**
```bash
docker logs gen_scraper-<name>-1
```

---

## Step 7: Initialize Database

### 7.1 Run Migrations

```bash
docker exec gen_scraper-backend-1 alembic upgrade head
```

**Expected:**
```
INFO  [alembic.runtime.migration] Running upgrade  -> 0001_initial_schema
INFO  [alembic.runtime.migration] Running upgrade 0001 -> 0002_extend_validated_results_table
...
```

### 7.2 Seed Database

```bash
docker exec gen_scraper-backend-1 python seed.py
```

**Expected:**
```
✓ Seeded 15 categories
✓ Seeded 25 sources
✓ Created admin user: admin@example.com
```

---

## Step 8: Verify System Works

### 8.1 Backend Health Check

```bash
curl http://localhost:8000/health
```

**Expected:** `{"status":"healthy"}`

### 8.2 Check Database

```bash
# Check categories
docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c "SELECT COUNT(*) FROM categories;"

# Check sources
docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c "SELECT name, is_active FROM sources ORDER BY name;"
```

**Expected:**
- ~15 categories
- ~25 sources

### 8.3 Open Frontend

Open browser: **http://localhost:5173**

### 8.4 Login

- Email: `admin@example.com`
- Password: `admin123`

---

## Step 9: Resume Work

All previous data is lost, but all code and configurations are intact.

**To resume scraping:**

```bash
# Check if bulk_job_creator.py exists
ls bulk_job_creator.py

# If it exists, run:
python bulk_job_creator.py --batch 1
```

---

## What Was Lost

**Data (can be re-scraped):**
- All scraped records
- All job history
- All user data (except admin user recreated by seed.py)

**NOT Lost (still in code):**
- All 25 source configurations
- All scraper implementations
- All database schema
- All tests
- All automation scripts
- All frontend code

---

## Troubleshooting

### "No space left on device" during build

**Cause:** Docker still using C: drive

**Solution:** Go back to Step 1 and configure E: drive properly

### "Cannot connect to Docker daemon"

**Cause:** Docker Desktop not running

**Solution:**
```bash
# Check if Docker is running
Get-Process | Where-Object {$_.Name -like "*docker*"}

# If not, start Docker Desktop manually
# Wait 2-3 minutes for full startup
```

### Postgres won't start

```bash
# Check logs
docker logs gen_scraper-postgres-1

# Common issue: port 5432 in use
netstat -ano | findstr :5432

# If something is using it, stop that service or change port in docker-compose.yml
```

### Worker won't start

```bash
# Check logs
docker logs gen_scraper-worker-1

# Common issue: RabbitMQ not ready yet
# Wait 30 seconds and check again
docker-compose restart worker
```

### Build fails with dependency errors

```bash
# Clean everything and rebuild
docker-compose down -v
docker system prune -a -f
docker-compose up -d --build
```

---

## Quick Reference

**Project Directory:** `C:\Users\DELL\Desktop\Gen_Scraper`

**Docker Data Location:** `E:\Docker` (after Step 1)

**URLs:**
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

**Admin Credentials:**
- Email: admin@example.com
- Password: admin123

**Key Commands:**
```bash
# Start containers
docker-compose up -d

# Stop containers
docker-compose down

# Rebuild everything
docker-compose up -d --build

# View logs
docker-compose logs -f

# Check status
docker-compose ps

# Restart a service
docker-compose restart <service-name>
```

---

## Recovery Checklist

- [ ] **Step 1:** Configure Docker to use E: drive
- [ ] **Step 2:** Verify E: drive has space (15+ GB)
- [ ] **Step 3:** Navigate to project directory
- [ ] **Step 4:** Rebuild containers (`docker-compose up -d --build`)
- [ ] **Step 5:** Wait for all containers to start
- [ ] **Step 6:** Run database migrations
- [ ] **Step 7:** Seed database
- [ ] **Step 8:** Verify system works
- [ ] **Step 9:** Resume work

---

## Estimated Timeline

- Step 1 (E: drive config): **5 minutes**
- Step 4 (Rebuild): **10-15 minutes**
- Steps 6-8 (Initialize): **3 minutes**
- **Total: ~20-25 minutes**

---

**Current Status:** Docker engine running, ready for Step 1

**Next Action:** Configure Docker to use E: drive (Step 1)
