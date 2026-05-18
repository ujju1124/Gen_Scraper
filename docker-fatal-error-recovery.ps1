# Docker Fatal Error Recovery Script
# Run this if Docker Desktop crashes with SIGBUS error

Write-Host "=== Docker Fatal Error Recovery ===" -ForegroundColor Cyan
Write-Host ""

# Step 1: Force kill all Docker processes
Write-Host "Step 1: Killing all Docker processes..." -ForegroundColor Yellow
Get-Process "*docker*" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 3

# Step 2: Check if processes are gone
$dockerProcesses = Get-Process "*docker*" -ErrorAction SilentlyContinue
if ($dockerProcesses) {
    Write-Host "WARNING: Some Docker processes still running" -ForegroundColor Red
    $dockerProcesses | Format-Table ProcessName, Id
} else {
    Write-Host "✓ All Docker processes stopped" -ForegroundColor Green
}

# Step 3: Wait for cleanup
Write-Host ""
Write-Host "Step 2: Waiting for system cleanup (10 seconds)..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

# Step 4: Restart Docker Desktop
Write-Host ""
Write-Host "Step 3: Starting Docker Desktop..." -ForegroundColor Yellow
Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"

Write-Host ""
Write-Host "Step 4: Waiting for Docker to initialize (30 seconds)..." -ForegroundColor Yellow
Start-Sleep -Seconds 30

# Step 5: Check if Docker is responding
Write-Host ""
Write-Host "Step 5: Checking Docker status..." -ForegroundColor Yellow
$dockerStatus = docker ps 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Docker is running!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Step 6: Starting containers..." -ForegroundColor Yellow
    Set-Location "C:\Users\DELL\Desktop\Gen_Scraper"
    docker-compose up -d
    Write-Host ""
    Write-Host "=== RECOVERY COMPLETE ===" -ForegroundColor Green
} else {
    Write-Host "✗ Docker is not responding yet" -ForegroundColor Red
    Write-Host "Error: $dockerStatus" -ForegroundColor Red
    Write-Host ""
    Write-Host "MANUAL STEPS REQUIRED:" -ForegroundColor Yellow
    Write-Host "1. Open Task Manager (Ctrl+Shift+Esc)"
    Write-Host "2. End all 'Docker Desktop' processes"
    Write-Host "3. Restart your computer"
    Write-Host "4. Start Docker Desktop manually"
    Write-Host "5. Run: docker-compose up -d"
}
