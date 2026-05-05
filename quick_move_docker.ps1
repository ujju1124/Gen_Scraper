# Quick Script to Move Docker to E: Drive
# Run as Administrator

Write-Host "=== Move Docker to E: Drive ===" -ForegroundColor Cyan
Write-Host ""

# Check if running as admin
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "✗ This script needs to run as Administrator" -ForegroundColor Red
    Write-Host "Right-click PowerShell → Run as Administrator" -ForegroundColor Yellow
    exit 1
}

Write-Host "✓ Running as Administrator" -ForegroundColor Green
Write-Host ""

# Step 1: Stop Docker
Write-Host "Step 1: Stopping Docker Desktop..." -ForegroundColor Yellow
Write-Host "Please quit Docker Desktop manually:" -ForegroundColor White
Write-Host "  1. Right-click Docker icon in system tray" -ForegroundColor Gray
Write-Host "  2. Click 'Quit Docker Desktop'" -ForegroundColor Gray
Write-Host ""
Read-Host "Press Enter when Docker Desktop is stopped"

# Step 2: Shutdown WSL
Write-Host ""
Write-Host "Step 2: Shutting down WSL..." -ForegroundColor Yellow
wsl --shutdown
Start-Sleep -Seconds 5
Write-Host "✓ WSL stopped" -ForegroundColor Green

# Step 3: Create directory on E:
Write-Host ""
Write-Host "Step 3: Creating directory on E: drive..." -ForegroundColor Yellow
New-Item -ItemType Directory -Path "E:\Docker\wsl" -Force | Out-Null
Write-Host "✓ Directory created: E:\Docker\wsl" -ForegroundColor Green

# Step 4: Check current WSL distributions
Write-Host ""
Write-Host "Step 4: Checking WSL distributions..." -ForegroundColor Yellow
wsl --list -v

# Step 5: Export distributions
Write-Host ""
Write-Host "Step 5: Exporting Docker distributions (this takes 5-10 minutes)..." -ForegroundColor Yellow

Write-Host "  Exporting docker-desktop..." -ForegroundColor Gray
wsl --export docker-desktop "E:\Docker\wsl\docker-desktop.tar"
Write-Host "  ✓ docker-desktop exported" -ForegroundColor Green

Write-Host "  Exporting docker-desktop-data..." -ForegroundColor Gray
wsl --export docker-desktop-data "E:\Docker\wsl\docker-desktop-data.tar"
Write-Host "  ✓ docker-desktop-data exported" -ForegroundColor Green

# Step 6: Unregister old distributions
Write-Host ""
Write-Host "Step 6: Unregistering old distributions..." -ForegroundColor Yellow
wsl --unregister docker-desktop
wsl --unregister docker-desktop-data
Write-Host "✓ Old distributions removed" -ForegroundColor Green

# Step 7: Import to new location
Write-Host ""
Write-Host "Step 7: Importing to E: drive (this takes 5-10 minutes)..." -ForegroundColor Yellow

Write-Host "  Importing docker-desktop..." -ForegroundColor Gray
wsl --import docker-desktop "E:\Docker\wsl\docker-desktop" "E:\Docker\wsl\docker-desktop.tar" --version 2
Write-Host "  ✓ docker-desktop imported" -ForegroundColor Green

Write-Host "  Importing docker-desktop-data..." -ForegroundColor Gray
wsl --import docker-desktop-data "E:\Docker\wsl\docker-desktop-data" "E:\Docker\wsl\docker-desktop-data.tar" --version 2
Write-Host "  ✓ docker-desktop-data imported" -ForegroundColor Green

# Step 8: Clean up tar files
Write-Host ""
Write-Host "Step 8: Cleaning up temporary files..." -ForegroundColor Yellow
Remove-Item "E:\Docker\wsl\docker-desktop.tar" -Force
Remove-Item "E:\Docker\wsl\docker-desktop-data.tar" -Force
Write-Host "✓ Temporary files removed" -ForegroundColor Green

# Step 9: Verify
Write-Host ""
Write-Host "Step 9: Verifying new location..." -ForegroundColor Yellow
wsl --list -v
Write-Host ""

# Step 10: Check disk space
Write-Host "Step 10: Checking disk space..." -ForegroundColor Yellow
$eDrive = Get-PSDrive E
Write-Host "E: drive free space: $([math]::Round($eDrive.Free / 1GB, 2)) GB" -ForegroundColor White
Write-Host ""

Write-Host "✓ Docker moved to E: drive successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "=== Next Steps ===" -ForegroundColor Cyan
Write-Host "1. Start Docker Desktop" -ForegroundColor White
Write-Host "2. Wait for it to fully start (2-3 minutes)" -ForegroundColor White
Write-Host "3. Run: .\rebuild.ps1" -ForegroundColor White
Write-Host ""
