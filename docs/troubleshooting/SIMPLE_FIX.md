# Simple Fix - Move Docker to E: Drive

## The Problem
- C: drive is full (only 9 GB free)
- Docker needs ~15 GB to work
- Docker keeps failing to start

## The Solution
Manually configure Docker to use E: drive through the UI.

---

## Steps (5 minutes)

### 1. Completely Stop Docker
```powershell
# Run in PowerShell
Stop-Process -Name "Docker Desktop" -Force -ErrorAction SilentlyContinue
wsl --shutdown
```

Wait 10 seconds.

### 2. Start Docker Desktop
- Double-click Docker Desktop icon on your desktop, OR
- Press Windows key, type "Docker Desktop", press Enter

### 3. Wait for Docker to Start
- Watch the whale icon in system tray
- Wait until it says "Docker Desktop is starting..." or shows the main window
- This takes 2-3 minutes

### 4. Open Settings
- Click the gear icon (⚙️) in top right of Docker Desktop
- Go to: **Settings**

### 5. Change Data Location
- Click **Resources** in left sidebar
- Click **Advanced**
- Look for **"Disk image location"** or **"Data directory"**
- Click **Browse** button
- Navigate to: `E:\Docker`
- Click **Select Folder**

### 6. Apply Changes
- Click **Apply & Restart** button at bottom
- Docker will restart (takes 3-5 minutes)
- **DO NOT CLOSE DOCKER** - let it restart

### 7. Wait for "Engine Running"
- Watch Docker Desktop window
- Wait until it says **"Engine running"** or **"Docker Desktop is running"**
- The whale icon in system tray should be stable (not animating)

### 8. Verify It Works
Open PowerShell and run:
```powershell
docker version
```

Should show version info without errors.

### 9. Build Your Project
```powershell
cd C:\Users\DELL\Desktop\Gen_Scraper
.\rebuild.ps1
```

This will build everything on E: drive with plenty of space!

---

## If Docker Won't Start At All

If Docker keeps failing to start:

### Option A: Uninstall and Reinstall
1. Uninstall Docker Desktop completely
2. Delete `C:\Users\DELL\AppData\Local\Docker`
3. Delete `C:\Users\DELL\AppData\Roaming\Docker`
4. Restart computer
5. Download Docker Desktop from: https://www.docker.com/products/docker-desktop
6. Install it
7. During first run, go to Settings and set data location to `E:\Docker`

### Option B: Free Up More Space on C:
1. Run Disk Cleanup (Windows key → type "Disk Cleanup")
2. Clean up Windows Update files
3. Delete old downloads
4. Empty Recycle Bin
5. Try starting Docker again

---

## What We've Already Done
✓ Freed up 9 GB on C: drive by deleting old Docker data
✓ Created E:\Docker directory
✓ Created settings file pointing to E: drive

## What You Need to Do
Just follow steps 1-9 above to manually configure Docker through the UI.

---

## Expected Result
- Docker running on E: drive
- C: drive has space
- `.\rebuild.ps1` completes successfully
- Application works at http://localhost:5173

---

**Start with Step 1 above!**
