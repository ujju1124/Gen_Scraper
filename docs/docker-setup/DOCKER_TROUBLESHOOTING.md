# Docker Desktop Troubleshooting

**Issue**: Docker Desktop is running but API is returning 500 errors

---

## Quick Fixes (Try in Order)

### Fix 1: Restart Docker Desktop (Proper Way)

1. **Open Docker Desktop** (not just the system tray icon)
2. Click the **Settings/Gear icon** (top right)
3. Go to **Troubleshoot** tab
4. Click **"Restart Docker Desktop"**
5. Wait 30-60 seconds for full restart

### Fix 2: Restart Docker Service

**Option A: Via PowerShell (as Administrator)**
```powershell
# Stop Docker
Stop-Service -Name "com.docker.service"

# Wait 5 seconds
Start-Sleep -Seconds 5

# Start Docker
Start-Service -Name "com.docker.service"

# Wait for Docker to be ready
Start-Sleep -Seconds 30

# Test
docker ps
```

**Option B: Via Services**
1. Press `Win + R`
2. Type `services.msc` and press Enter
3. Find "Docker Desktop Service"
4. Right-click → Restart
5. Wait 30 seconds

### Fix 3: Restart WSL2 Backend

```powershell
# Shutdown WSL
wsl --shutdown

# Wait 10 seconds
Start-Sleep -Seconds 10

# Start Docker Desktop again
# (It will restart WSL automatically)
```

### Fix 4: Full Computer Restart

Sometimes Docker Desktop gets into a bad state. A full restart usually fixes it:
1. Close Docker Desktop
2. Restart your computer
3. Start Docker Desktop
4. Wait for it to fully initialize (whale icon stops animating)

---

## Verify Docker is Working

After trying any fix, test with:

```powershell
# Check Docker version
docker version

# Check running containers
docker ps

# Check Docker info
docker info
```

All three commands should work without errors.

---

## Once Docker is Working

### Step 1: Start Containers

```bash
cd C:\Users\DELL\Desktop\Gen_Scraper
docker-compose up -d
```

### Step 2: Verify All Containers Running

```bash
docker ps
```

You should see 5 containers:
- gen_scraper-postgres-1 (healthy)
- gen_scraper-redis-1 (healthy)
- gen_scraper-backend-1 (running)
- gen_scraper-worker-1 (running)
- gen_scraper-frontend-1 (running)

### Step 3: Check Existing Jobs

```bash
docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c "SELECT status, COUNT(*) FROM scrape_jobs GROUP BY status;"
```

### Step 4: Run Bulk Collection

```bash
docker exec gen_scraper-backend-1 python scripts/bulk_collect_simple.py
```

---

## Common Docker Desktop Issues

### Issue: "Docker Desktop is starting..."

**Solution**: Wait 2-3 minutes. Docker Desktop takes time to start, especially after a restart.

### Issue: "WSL 2 installation is incomplete"

**Solution**: 
1. Open PowerShell as Administrator
2. Run: `wsl --update`
3. Restart computer

### Issue: "Docker daemon is not running"

**Solution**:
1. Open Docker Desktop application
2. Wait for it to fully start
3. Check system tray icon - should be solid (not animated)

### Issue: "Cannot connect to Docker daemon"

**Solution**:
1. Check Docker Desktop is running
2. Try: `wsl --shutdown` then restart Docker Desktop
3. Check Windows Services - "Docker Desktop Service" should be running

### Issue: "Error response from daemon: Get https://registry-1.docker.io/v2/: net/http: request canceled"

**Solution**:
1. Check internet connection
2. Docker Desktop → Settings → Resources → Network
3. Try changing DNS to 8.8.8.8

---

## If Nothing Works

### Nuclear Option: Reinstall Docker Desktop

⚠️ **This will delete all containers and images** (but your code is safe)

1. Backup any important data
2. Uninstall Docker Desktop
3. Delete `C:\Users\DELL\AppData\Local\Docker`
4. Delete `C:\Users\DELL\AppData\Roaming\Docker`
5. Restart computer
6. Install Docker Desktop fresh
7. Configure to use E: drive (see MOVE_DOCKER_TO_E_DRIVE.md)
8. Rebuild: `docker-compose up --build`

---

## Current Status Check

Run this to see what's happening:

```powershell
# Check Docker service
Get-Service -Name "com.docker.service"

# Check WSL status
wsl --list --verbose

# Check Docker Desktop process
Get-Process -Name "Docker Desktop" -ErrorAction SilentlyContinue

# Try Docker command
docker version
```

---

## Contact Info

If you're still stuck, the error message usually tells you what's wrong:
- "500 Internal Server Error" = Docker engine not fully started
- "Cannot connect" = Docker daemon not running
- "WSL" errors = WSL2 backend issue

**Most common fix**: Just wait 2-3 minutes after starting Docker Desktop. It takes time to initialize.
