# Emergency Docker Recovery Script
# Run this when Docker Desktop disconnects

Write-Host "🚨 Starting Docker Emergency Recovery..." -ForegroundColor Yellow
Write-Host ""

# Step 1: Stop Docker Desktop
Write-Host "[1/7] Stopping Docker Desktop..." -ForegroundColor Cyan
Stop-Process -Name "Docker Desktop" -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 3

# Step 2: Shutdown WSL
Write-Host "[2/7] Shutting down WSL..." -ForegroundColor Cyan
wsl --shutdown
Start-Sleep -Seconds 5

# Step 3: Start Docker Desktop
Write-Host "[3/7] Starting Docker Desktop..." -ForegroundColor Cyan
Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"

# Step 4: Wait for Docker to be ready
Write-Host "[4/7] Waiting for Docker to be ready..." -ForegroundColor Cyan
$maxAttempts = 30
$attempt = 0
while ($attempt -lt $maxAttempts) {
    $dockerStatus = docker info 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "      ✅ Docker is ready!" -ForegroundColor Green
        break
    }
    $attempt++
    Write-Host "      Attempt $attempt/$maxAttempts..." -ForegroundColor Yellow
    Start-Sleep -Seconds 5
}

if ($attempt -eq $maxAttempts) {
    Write-Host "      ❌ Docker failed to start after $maxAttempts attempts" -ForegroundColor Red
    Write-Host ""
    Write-Host "Manual steps required:" -ForegroundColor Yellow
    Write-Host "1. Open Docker Desktop manually" -ForegroundColor Yellow
    Write-Host "2. Wait for it to start" -ForegroundColor Yellow
    Write-Host "3. Run: docker-compose up -d" -ForegroundColor Yellow
    exit 1
}

# Step 5: Navigate to project directory
Write-Host "[5/7] Navigating to project directory..." -ForegroundColor Cyan
Set-Location "C:\Users\DELL\Desktop\Gen_Scraper"

# Step 6: Start containers
Write-Host "[6/7] Starting containers..." -ForegroundColor Cyan
docker-compose up -d

# Step 7: Verify
Write-Host "[7/7] Verifying containers..." -ForegroundColor Cyan
Write-Host ""
docker-compose ps
Write-Host ""

# Check job status
Write-Host "Checking job status..." -ForegroundColor Cyan
docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c "SELECT status, COUNT(*) FROM scrape_jobs WHERE status != 'CANCELLED' GROUP BY status ORDER BY status;"

Write-Host ""
Write-Host "✅ Recovery complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Monitor worker logs: docker-compose logs -f worker" -ForegroundColor White
Write-Host "2. Check job progress in 10 minutes" -ForegroundColor White
Write-Host "3. If issues persist, see DOCKER_DESKTOP_DISCONNECT_FIX.md" -ForegroundColor White
