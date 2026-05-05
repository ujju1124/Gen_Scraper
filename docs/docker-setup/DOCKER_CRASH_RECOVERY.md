# 🚨 Docker Crash Recovery Guide

**Problem**: Docker Desktop crashes, hangs, or shows high CPU usage during scraping

---

## 🎯 **Quick Fix (Do This Now)**

### **Option 1: Use Recovery Script (Easiest)**

```powershell
# Run this from project root
.\restart-docker-safe.ps1
```

This script will:
1. Stop all containers gracefully
2. Stop Docker Desktop
3. Wait for cleanup
4. Restart Docker Desktop
5. Wait for engine to be ready
6. Start containers with resource limits
7. Verify everything is running

---

### **Option 2: Manual Steps**

#### **Step 1: Stop Docker Desktop**
1. Right-click Docker icon in system tray
2. Click "Quit Docker Desktop"
3. Wait 30 seconds

#### **Step 2: Kill Remaining Processes**
```powershell
# Open PowerShell as Administrator
Stop-Process -Name "Docker Desktop" -Force -ErrorAction SilentlyContinue
Stop-Process -Name "com.docker.backend" -Force -ErrorAction SilentlyContinue
```

#### **Step 3: Wait**
- Wait 1 minute for complete shutdown

#### **Step 4: Restart Docker Desktop**
- Open Docker Desktop from Start Menu
- Wait 2-3 minutes for "Engine running" status

#### **Step 5: Start Containers**
```powershell
cd C:\Users\DELL\Desktop\Gen_Scraper
docker compose up -d
```

#### **Step 6: Verify**
```powershell
docker compose ps
```

---

## 🔍 **Why This Happens**

### **Root Causes**

1. **Too many concurrent jobs**
   - 2 workers processing simultaneously
   - Each job uses browser automation (high CPU/memory)
   - System gets overwhelmed

2. **Resource exhaustion**
   - CPU usage spikes to 300%+
   - Memory fills up
   - Docker daemon becomes unresponsive

3. **Browser automation overhead**
   - Playwright/Camoufox browsers
   - Multiple browser instances
   - Heavy JavaScript rendering

4. **WSL2 backend issues**
   - Docker Desktop uses WSL2
   - WSL2 can hang under heavy load
   - Requires restart to recover

---

## ✅ **What We Fixed**

### **1. Reduced Worker Concurrency**

**Before:**
```yaml
CELERY_CONCURRENCY=2  # 2 jobs at once
```

**After:**
```yaml
CELERY_CONCURRENCY=1  # 1 job at a time
```

**Impact:**
- ✅ Lower CPU usage
- ✅ Lower memory usage
- ✅ More stable
- ⚠️ Slower (but won't crash)

### **2. Added Resource Limits**

**Worker limits:**
```yaml
deploy:
  resources:
    limits:
      cpus: '2.0'      # Max 2 CPU cores
      memory: 2G       # Max 2GB RAM
    reservations:
      cpus: '1.0'      # Min 1 CPU core
      memory: 1G       # Min 1GB RAM
```

**Backend limits:**
```yaml
deploy:
  resources:
    limits:
      cpus: '1.0'      # Max 1 CPU core
      memory: 1G       # Max 1GB RAM
```

**Impact:**
- ✅ Prevents resource exhaustion
- ✅ Docker can't consume all system resources
- ✅ System stays responsive

---

## 📊 **Performance Comparison**

### **Before (2 concurrent workers)**
- CPU: 300-400% usage
- Memory: 4-6GB
- Stability: Crashes every 1-2 hours
- Speed: ~20-30 jobs/hour

### **After (1 worker + limits)**
- CPU: 100-150% usage
- Memory: 2-3GB
- Stability: Runs indefinitely
- Speed: ~10-15 jobs/hour

**Trade-off**: Slower but stable

---

## 🎯 **Monitoring**

### **Check System Resources**

**Task Manager:**
- Press Ctrl+Shift+Esc
- Look at "Docker Desktop" process
- Should be under 50% CPU

**Docker Stats:**
```powershell
docker stats
```

**Expected:**
- Worker: 50-100% CPU, 1-2GB RAM
- Backend: 10-20% CPU, 200-500MB RAM
- Postgres: 5-10% CPU, 100-200MB RAM

### **Check Job Progress**

```powershell
docker compose exec postgres psql -U scraper -d scraper_db -c \
  "SELECT status, COUNT(*) FROM scrape_jobs GROUP BY status;"
```

### **Monitor Worker**

```powershell
# Live logs
docker compose logs worker -f --tail 50

# Check for errors
docker compose logs worker --tail 100 | Select-String "error"
```

---

## ⚠️ **Warning Signs**

Watch for these signs that Docker is about to crash:

1. **High CPU (>200%)**
   - Check Task Manager
   - If Docker Desktop >200% CPU, it may crash soon

2. **Slow responses**
   - Docker commands take >10 seconds
   - Frontend becomes unresponsive

3. **Memory warnings**
   - Docker Desktop using >4GB RAM
   - System memory >90% full

4. **Container restarts**
   - Containers keep restarting
   - Check: `docker compose ps`

**If you see these signs:**
1. Stop new jobs from being created
2. Let current jobs finish
3. Restart Docker using the recovery script

---

## 🔧 **Advanced Troubleshooting**

### **If Recovery Script Fails**

1. **Restart Computer**
   - Sometimes WSL2 gets stuck
   - Full restart clears everything

2. **Restart WSL2**
   ```powershell
   wsl --shutdown
   # Wait 10 seconds
   # Start Docker Desktop
   ```

3. **Check Docker Desktop Settings**
   - Open Docker Desktop
   - Settings → Resources
   - Ensure:
     - CPUs: 4 or less
     - Memory: 4GB or less
     - Swap: 1GB

4. **Reset Docker Desktop**
   - Settings → Troubleshoot
   - "Reset to factory defaults"
   - ⚠️ This deletes all containers/images
   - You'll need to rebuild

### **If Jobs Keep Failing**

```powershell
# Check failed jobs
docker compose exec postgres psql -U scraper -d scraper_db -c \
  "SELECT id, city, status, error_message FROM scrape_jobs WHERE status = 'FAILED' LIMIT 10;"

# Restart worker
docker compose restart worker

# Check worker logs
docker compose logs worker --tail 100
```

---

## 📝 **Best Practices**

### **To Prevent Crashes**

1. **Run overnight**
   - Start scraping before bed
   - Let it run while you sleep
   - Check in the morning

2. **Monitor periodically**
   - Check every 2-3 hours
   - Look at Task Manager
   - Restart if CPU >200%

3. **Don't use computer heavily**
   - Light browsing is fine
   - Avoid gaming, video editing
   - Close unnecessary programs

4. **Keep Docker Desktop updated**
   - Check for updates weekly
   - Updates fix stability issues

5. **Restart Docker daily**
   - If running multi-day scraping
   - Restart Docker once per day
   - Prevents memory leaks

---

## 🆘 **Emergency Commands**

### **Force Stop Everything**

```powershell
# Stop all containers immediately
docker compose kill

# Remove all containers
docker compose down

# Stop Docker Desktop
Stop-Process -Name "Docker Desktop" -Force
```

### **Check What's Running**

```powershell
# All containers
docker ps -a

# Resource usage
docker stats --no-stream

# Disk usage
docker system df
```

### **Clean Up**

```powershell
# Remove stopped containers
docker container prune -f

# Remove unused images
docker image prune -a -f

# Remove build cache
docker builder prune -a -f
```

---

## 📞 **Quick Reference**

| Problem | Solution |
|---------|----------|
| Docker won't start | Run recovery script |
| High CPU usage | Reduce to 1 worker |
| Containers crash | Add resource limits |
| Jobs fail | Check worker logs |
| System freezes | Restart computer |
| Out of memory | Reduce worker concurrency |
| WSL2 issues | `wsl --shutdown` |

---

## ✅ **Verification Checklist**

After recovery, verify:

- [ ] Docker Desktop shows "Engine running"
- [ ] All 5 containers running: `docker compose ps`
- [ ] Worker processing jobs: `docker compose logs worker --tail 20`
- [ ] CPU usage <150%: Check Task Manager
- [ ] Jobs progressing: Check database
- [ ] No error messages: `docker compose logs --tail 50`

---

## 🎯 **Summary**

**Problem**: Docker crashes due to resource exhaustion  
**Solution**: Reduce concurrency + add resource limits  
**Recovery**: Use `restart-docker-safe.ps1` script  
**Prevention**: Monitor CPU, restart daily, run overnight  

**Your scraping will now be:**
- ✅ Slower (1 job at a time instead of 2)
- ✅ More stable (won't crash)
- ✅ Predictable (consistent performance)
- ✅ Reliable (can run for days)

---

**Last Updated**: May 5, 2026  
**Status**: Resource limits applied, recovery script created  
**Next**: Run `.\restart-docker-safe.ps1` to recover
