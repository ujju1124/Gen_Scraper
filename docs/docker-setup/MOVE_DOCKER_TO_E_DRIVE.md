# Move Docker to E: Drive

## Why This Matters
Docker stores all images, containers, and volumes on C: drive by default. This can consume 10-20 GB easily. Moving to E: drive will solve the space issue.

---

## Step-by-Step Guide

### Step 1: Stop Docker Desktop
1. Right-click Docker Desktop icon in system tray
2. Click "Quit Docker Desktop"
3. Wait for it to fully stop

### Step 2: Open Docker Desktop Settings
1. Start Docker Desktop again
2. Click the gear icon (⚙️) in top right → Settings
3. Go to **Resources** → **Advanced**

### Step 3: Change Data Directory
1. Look for "Disk image location" or "Docker data directory"
2. Click "Browse" or the folder icon
3. Navigate to: `E:\Docker`
4. Click "Select Folder"
5. Click "Apply & Restart"

**Docker will now move all data to E: drive. This takes 5-10 minutes.**

---

## Alternative Method (If Settings Don't Work)

### Manual Move via WSL2

If Docker uses WSL2 backend, you need to move the WSL2 virtual disk:

```powershell
# 1. Stop Docker Desktop completely
# Right-click tray icon → Quit Docker Desktop

# 2. Shut down WSL

wsl --shutdown

# 3. Create directory on E: drive
New-Item -ItemType Directory -Path "E:\Docker\wsl" -Force

# 4. Export WSL distribution
wsl --export docker-desktop "E:\Docker\wsl\docker-desktop.tar"
wsl --export docker-desktop-data "E:\Docker\wsl\docker-desktop-data.tar"

# 5. Unregister old distributions
wsl --unregister docker-desktop
wsl --unregister docker-desktop-data

# 6. Import to new location
wsl --import docker-desktop "E:\Docker\wsl\docker-desktop" "E:\Docker\wsl\docker-desktop.tar" --version 2
wsl --import docker-desktop-data "E:\Docker\wsl\docker-desktop-data" "E:\Docker\wsl\docker-desktop-data.tar" --version 2

# 7. Clean up tar files (optional)
Remove-Item "E:\Docker\wsl\docker-desktop.tar"
Remove-Item "E:\Docker\wsl\docker-desktop-data.tar"

# 8. Start Docker Desktop
```

---

## Step 4: Verify New Location

After Docker restarts:

```powershell
# Check WSL distributions
wsl --list -v

# Should show docker-desktop and docker-desktop-data
```

---

## Step 5: Clean Up C: Drive

Once Docker is working on E: drive:

```powershell
# Remove old Docker data from C: drive
# Location is usually: C:\Users\DELL\AppData\Local\Docker

# Check size first
Get-ChildItem "C:\Users\DELL\AppData\Local\Docker" -Recurse | Measure-Object -Property Length -Sum

# If Docker is working on E:, you can delete this
Remove-Item "C:\Users\DELL\AppData\Local\Docker" -Recurse -Force
```

---

## Step 6: Rebuild Everything

Once Docker is on E: drive with plenty of space:

```powershell
# Navigate to project
cd C:\Users\DELL\Desktop\Gen_Scraper

# Run the rebuild script
.\rebuild.ps1
```

This will now work because you have space on E: drive!

---

## Disk Space Requirements

**Minimum recommended:**
- Docker images: ~5 GB
- Build cache: ~3 GB
- Containers: ~2 GB
- Working space: ~5 GB
- **Total: ~15 GB free on E: drive**

---

## Troubleshooting

### Problem: Can't find "Disk image location" in settings
**Solution:** You're using WSL2 backend. Use the "Alternative Method" above.

### Problem: WSL commands fail
**Solution:** 
```powershell
# Enable WSL if not enabled
wsl --install

# Update WSL
wsl --update
```

### Problem: Docker won't start after move
**Solution:**
```powershell
# Reset Docker Desktop
# Settings → Troubleshoot → Reset to factory defaults
# Then repeat the move process
```

### Problem: "Access denied" errors
**Solution:** Run PowerShell as Administrator

---

## Quick Checklist

- [ ] Stop Docker Desktop
- [ ] Move data to E:\Docker (via Settings or WSL)
- [ ] Start Docker Desktop
- [ ] Verify it works: `docker version`
- [ ] Clean up C: drive
- [ ] Run `.\rebuild.ps1`
- [ ] Wait 15-20 minutes
- [ ] Access app at http://localhost:5173

---

## Expected Timeline

1. Move Docker to E: drive: **10 minutes**
2. Rebuild all containers: **15-20 minutes**
3. **Total: ~30 minutes**

But you'll have a working system with plenty of space!

---

**Ready to start?** Follow Step 1 above!
