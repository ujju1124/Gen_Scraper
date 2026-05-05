# Docker Recovery Guide

## What Happened
Docker was reinstalled, which wiped:
- ✗ All containers (0 containers)
- ✗ All images (0 images)
- ✗ All volumes (database data lost)
- ✗ All networks

## What's Still Safe
- ✓ All source code
- ✓ All scraper implementations
- ✓ Database schema (in migrations)
- ✓ All configuration files
- ✓ All automation scripts

---

## Recovery Steps

### Step 1: Wait for Docker Desktop to Fully Start

**Check the Docker Desktop icon in your system tray:**
- The whale icon should be **stable** (not animating)
- Right-click the icon and verify it says "Docker Desktop is running"

**This is critical!** If Docker is still starting, the recovery script will fail.

---

### Step 2: Run the Automated Recovery Script

Open PowerShell in the project directory and run:

```powershell
.\rebuild.ps1
```

**What this script does:**
1. ✓ Verifies Docker is running
2. ✓ Cleans up any partial state
3. ✓ Builds backend image (~5 minutes)
4. ✓ Builds frontend image (~3 minutes)
5. ✓ Starts all 6 containers:
   - postgres (database)
   - redis (cache)
   - backend (API)
   - frontend (UI)
   - celery-worker (background jobs)
   - celery-beat (scheduler)
6. ✓ Waits for PostgreSQL to be ready
7. ✓ Runs database migrations
8. ✓ Seeds initial data:
   - 3 categories (Hotels, Restaurants, Services)
   - 9 active sources (Booking.com, Agoda, Google Maps, etc.)
   - Admin user (admin@example.com / admin123)
9. ✓ Verifies everything is working

**Expected time:** 15-20 minutes total

---

### Step 3: Verify Recovery

After the script completes, verify:

1. **Check containers are running:**
   ```powershell
   docker-compose ps
   ```
   Should show 6 containers in "Up" state

2. **Check backend logs:**
   ```powershell
   docker logs gen_scraper-backend-1 --tail 50
   ```
   Should show "Application startup complete"

3. **Open the application:**
   - URL: http://localhost:5173
   - Login: admin@example.com / admin123
   - You should see the dashboard

---

### Step 4: Resume Scraping Operations

Once verified, you can start fresh:

```bash
# Start Batch 1 (Hotels in Kathmandu)
python bulk_job_creator.py --batch 1

# Monitor progress
python monitor_batch1.py
```

---

## Troubleshooting

### Problem: "Docker is not running"
**Solution:** Wait longer for Docker Desktop to fully start. Check the system tray icon.

### Problem: Build fails with "no space left on device"
**Solution:** 
```powershell
docker system prune -a --volumes
```
Then run `.\rebuild.ps1` again.

### Problem: PostgreSQL won't start
**Solution:**
```powershell
# Check logs
docker logs gen_scraper-postgres-1

# If port 5432 is in use, stop other PostgreSQL instances
# Then restart
docker-compose restart postgres
```

### Problem: Backend fails to start
**Solution:**
```powershell
# Check logs
docker logs gen_scraper-backend-1

# Common issues:
# 1. Database not ready - wait 30 seconds and check again
# 2. Port 8000 in use - stop other services using that port
```

### Problem: Frontend shows blank page
**Solution:**
```powershell
# Check if backend is accessible
curl http://localhost:8000/health

# Check frontend logs
docker logs gen_scraper-frontend-1

# Rebuild frontend if needed
docker-compose build frontend
docker-compose up -d frontend
```

---

## Manual Recovery (If Script Fails)

If the automated script fails, you can run steps manually:

```powershell
# 1. Build images
docker-compose build

# 2. Start containers
docker-compose up -d

# 3. Wait for postgres (30 seconds)
Start-Sleep -Seconds 30

# 4. Run migrations
docker exec gen_scraper-backend-1 alembic upgrade head

# 5. Seed database
docker exec gen_scraper-backend-1 python seed.py

# 6. Verify
docker-compose ps
```

---

## Data Loss Summary

**Lost:**
- All previous scrape jobs
- All scraped results (raw, cleaned, validated)
- All user sessions

**Not Lost:**
- Source code
- Scraper implementations
- Configuration
- The ability to re-scrape everything

**Impact:**
- You'll need to re-run all scraping jobs
- Previous results are gone, but can be regenerated
- No code changes needed

---

## Prevention for Future

To avoid losing data in the future:

1. **Regular backups:**
   ```powershell
   # Backup database
   docker exec gen_scraper-postgres-1 pg_dump -U scraper scraper_db > backup.sql
   ```

2. **Export results before major changes:**
   ```bash
   # Export validated results
   python export_results.py
   ```

3. **Use Docker volumes for persistence** (already configured in docker-compose.yml)

---

## Quick Reference

**Check Docker status:**
```powershell
docker version
docker-compose ps
```

**View logs:**
```powershell
docker logs gen_scraper-backend-1 --tail 50 -f
docker logs gen_scraper-postgres-1 --tail 50 -f
```

**Restart services:**
```powershell
docker-compose restart backend
docker-compose restart postgres
```

**Complete reset:**
```powershell
docker-compose down -v
.\rebuild.ps1
```

---

## Support

If you encounter issues not covered here:

1. Check container logs: `docker logs <container-name>`
2. Check Docker Desktop logs: Settings → Troubleshoot → View logs
3. Verify disk space: `docker system df`
4. Check port conflicts: `netstat -ano | findstr "5432 8000 5173"`

---

**Ready to recover?** Run `.\rebuild.ps1` when Docker Desktop is fully started!
