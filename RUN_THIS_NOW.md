# 🚨 CRITICAL: Run Memory Fix Now

## Current Status
- **Worker Memory**: 1.999GB/2GB (99.97% - **ABOUT TO CRASH!**)
- **System**: Docker with WSL2 backend (no memory slider in UI)
- **Solution**: Configure WSL2 memory via `.wslconfig` file

---

## ✅ Run Automated Fix Script

Open PowerShell in this directory and run:

```powershell
.\fix-memory-issue.ps1
```

### What the script does:
1. ✅ Stops Docker containers
2. ✅ Creates `.wslconfig` file at `C:\Users\DELL\.wslconfig`
3. ✅ Shuts down WSL2 to apply new settings
4. ✅ Waits for Docker to restart
5. ✅ Starts containers with 4GB memory limit
6. ✅ Re-queues all 161 pending jobs
7. ✅ Shows memory stats to verify fix

### Expected Result:
```
CONTAINER           CPU %    MEM USAGE / LIMIT     MEM %
gen_scraper-worker  50%      2GB / 4GB            50%     ✅ SAFE!
```

Instead of:
```
gen_scraper-worker  100%     1.999GB / 2GB        99.97%  ❌ CRITICAL!
```

---

## 📊 After Fix - Check Status

### Memory:
```powershell
docker stats --no-stream
```

### Records:
```powershell
docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c "SELECT COUNT(*) FROM cleaned_results;"
```

### Jobs:
```powershell
docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c "SELECT status, COUNT(*) FROM scrape_jobs GROUP BY status;"
```

---

## 🎯 What Changed

### Before:
- WSL2 Memory: **2GB** (default)
- Worker Limit: 2GB
- Worker Usage: 1.999GB (99.97% - **CRITICAL!**)

### After:
- WSL2 Memory: **4GB** (via `.wslconfig`)
- Worker Limit: 4GB
- Worker Usage: ~2GB (50% - **SAFE!**)

---

## 📝 Technical Details

### .wslconfig File Created:
**Location**: `C:\Users\DELL\.wslconfig`

**Contents**:
```ini
[wsl2]
memory=4GB
processors=4
swap=2GB
localhostForwarding=true
```

This tells WSL2 to allow Docker to use up to 4GB of RAM.

### docker-compose.yml Already Updated:
```yaml
worker:
  deploy:
    resources:
      limits:
        memory: 4G  # ✅ Already set
```

Both WSL2 and docker-compose need to allow 4GB for it to work.

---

## ⏱️ Timeline

**Script Runtime**: ~2-3 minutes
- Stop containers: 10 seconds
- Create .wslconfig: 1 second
- Shutdown WSL2: 5 seconds
- Wait for Docker: 30-60 seconds
- Start containers: 30 seconds
- Re-queue jobs: 10 seconds
- Verify: 5 seconds

**After Fix**:
- Scraping continues safely
- No crash risk
- Same speed (~64 records/hour)
- 161 jobs remaining (~40-50 hours total)

---

## 🚀 Run It Now!

```powershell
.\fix-memory-issue.ps1
```

**Then monitor for 5 minutes to ensure stability:**
```powershell
docker stats
```

Press `Ctrl+C` to stop monitoring.

---

## ❓ If Script Fails

### Manual Steps:

1. **Stop containers:**
   ```powershell
   docker compose down
   ```

2. **Create .wslconfig file:**
   - Open Notepad
   - Paste:
     ```
     [wsl2]
     memory=4GB
     processors=4
     swap=2GB
     localhostForwarding=true
     ```
   - Save as: `C:\Users\DELL\.wslconfig`
   - Make sure it's `.wslconfig` not `.wslconfig.txt`

3. **Shutdown WSL2:**
   ```powershell
   wsl --shutdown
   ```

4. **Wait 30 seconds**, then open Docker Desktop

5. **Start containers:**
   ```powershell
   docker compose up -d
   ```

6. **Wait 30 seconds**, then re-queue:
   ```powershell
   docker exec gen_scraper-backend-1 python requeue_jobs.py
   ```

7. **Verify:**
   ```powershell
   docker stats --no-stream
   ```

---

## 📞 Need Help?

If you see any errors, paste them and I'll help troubleshoot.

**Common Issues:**
- "Docker not running" → Open Docker Desktop manually
- "Container not found" → Wait 30 more seconds, try again
- "Permission denied" → Run PowerShell as Administrator

---

**DO THIS NOW BEFORE WORKER CRASHES!** 🚨
