# Reinstall Docker Desktop - Clean Installation

## What We've Done
✓ Uninstalled Docker Desktop
✓ Removed all Docker files from C: drive
✓ Freed up 13.12 GB on C: drive
✓ Removed WSL distributions

## Now You Need To:

### Step 1: Download Docker Desktop
1. Open browser
2. Go to: https://www.docker.com/products/docker-desktop/
3. Click "Download for Windows"
4. Wait for download to complete (500 MB file)

### Step 2: Install Docker Desktop
1. Find the downloaded file: `Docker Desktop Installer.exe`
2. **Right-click** → **Run as Administrator**
3. Follow the installation wizard:
   - ✓ Use WSL 2 instead of Hyper-V (recommended)
   - ✓ Add shortcut to desktop
4. Click "Install"
5. Wait for installation (5-10 minutes)
6. Click "Close" when done
7. **Restart your computer** (required!)

### Step 3: First Launch (After Restart)
1. Double-click Docker Desktop icon
2. Accept the service agreement
3. **Skip the tutorial** (click Skip or Close)
4. Wait for Docker to start (2-3 minutes)
5. You should see "Docker Desktop is running"

### Step 4: Configure to Use E: Drive
**IMPORTANT: Do this immediately after first start!**

1. Click the gear icon (⚙️) in top right
2. Go to: **Settings** → **Resources** → **Advanced**
3. Find **"Disk image location"**
4. Click **Browse**
5. Navigate to: `E:\Docker`
6. Click **Select Folder**
7. Click **Apply & Restart**
8. Wait for Docker to restart (3-5 minutes)

### Step 5: Verify Docker Works
Open PowerShell and run:
```powershell
docker version
```

Should show version info without errors.

### Step 6: Build Your Project
```powershell
cd C:\Users\DELL\Desktop\Gen_Scraper
.\rebuild.ps1
```

This will:
- Build all Docker images on E: drive
- Start all containers
- Run migrations
- Seed database
- Takes 15-20 minutes

### Step 7: Access Your Application
- Open browser: http://localhost:5173
- Login: admin@example.com / admin123
- Start scraping!

---

## Troubleshooting

### Problem: "WSL 2 installation is incomplete"
**Solution:**
```powershell
wsl --install
wsl --update
```
Then restart computer and try Docker again.

### Problem: "Docker Desktop requires Windows 10/11"
**Solution:** Update Windows to latest version.

### Problem: Docker starts but can't run containers
**Solution:** 
1. Open Docker Desktop
2. Settings → Troubleshoot → Reset to factory defaults
3. Restart Docker

---

## Why This Will Work Now

**Before:**
- ✗ C: drive was full (0 GB free)
- ✗ Docker couldn't create files
- ✗ Corrupted installation

**Now:**
- ✓ C: drive has 13 GB free
- ✓ Clean installation
- ✓ Will configure to use E: drive immediately
- ✓ E: drive has 242 GB free

---

## Timeline

1. Download Docker: **5 minutes**
2. Install Docker: **10 minutes**
3. Restart computer: **2 minutes**
4. First launch + configure: **5 minutes**
5. Build project: **20 minutes**

**Total: ~45 minutes**

---

**Start with Step 1: Download Docker Desktop!**

Once you've installed and configured it, come back and run `.\rebuild.ps1`
