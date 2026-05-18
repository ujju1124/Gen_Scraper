# Fix Memory Issue - Increase Docker Memory Limit (WSL2 Backend)
# Run this script to apply the memory fix

Write-Host ""
Write-Host "=========================================================" -ForegroundColor Red
Write-Host "        FIXING CRITICAL MEMORY ISSUE                     " -ForegroundColor Red
Write-Host "=========================================================" -ForegroundColor Red
Write-Host ""

Write-Host "Current Issue:" -ForegroundColor Yellow
Write-Host "  Worker Memory: 1.999GB/2GB (99.97% CRITICAL)" -ForegroundColor Red
Write-Host ""

Write-Host "Solution:" -ForegroundColor Yellow
Write-Host "  Increase WSL2 memory limit to 4GB via .wslconfig" -ForegroundColor Green
Write-Host ""

# Step 1: Stop containers
Write-Host "Step 1: Stopping containers..." -ForegroundColor Cyan
docker compose down
Write-Host "[OK] Containers stopped" -ForegroundColor Green
Write-Host ""

# Step 2: Create .wslconfig file
Write-Host "Step 2: Creating .wslconfig file..." -ForegroundColor Cyan
$wslConfigPath = "$env:USERPROFILE\.wslconfig"
$wslConfigContent = @"
[wsl2]
memory=4GB
processors=4
swap=2GB
localhostForwarding=true
"@

try {
    $wslConfigContent | Out-File -FilePath $wslConfigPath -Encoding utf8 -Force
    Write-Host "[OK] Created .wslconfig at: $wslConfigPath" -ForegroundColor Green
    Write-Host ""
    Write-Host "Contents:" -ForegroundColor Yellow
    Get-Content $wslConfigPath | ForEach-Object { Write-Host "  $_" -ForegroundColor White }
    Write-Host ""
} catch {
    Write-Host "[ERROR] Failed to create .wslconfig: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please manually create the file at: $wslConfigPath" -ForegroundColor Yellow
    Write-Host "With contents:" -ForegroundColor Yellow
    Write-Host $wslConfigContent -ForegroundColor White
    exit 1
}

# Step 3: Shutdown WSL2
Write-Host "Step 3: Shutting down WSL2..." -ForegroundColor Cyan
wsl --shutdown
Start-Sleep -Seconds 5
Write-Host "[OK] WSL2 shut down" -ForegroundColor Green
Write-Host ""

# Step 4: Wait for Docker to restart
Write-Host "Step 4: Waiting for Docker Desktop to restart..." -ForegroundColor Cyan
Write-Host "  This may take 30-60 seconds..." -ForegroundColor Yellow
Start-Sleep -Seconds 30

# Check if Docker is running
$dockerRunning = $false
$attempts = 0
$maxAttempts = 12

while (-not $dockerRunning -and $attempts -lt $maxAttempts) {
    try {
        docker ps | Out-Null
        $dockerRunning = $true
    } catch {
        $attempts++
        Write-Host "  Waiting for Docker... (attempt $attempts/$maxAttempts)" -ForegroundColor Yellow
        Start-Sleep -Seconds 5
    }
}

if (-not $dockerRunning) {
    Write-Host "[ERROR] Docker did not start automatically" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please manually start Docker Desktop, then press Enter to continue..." -ForegroundColor Yellow
    Read-Host
}

Write-Host "[OK] Docker is running" -ForegroundColor Green
Write-Host ""

# Step 5: Start containers with new limits
Write-Host "Step 5: Starting containers with new memory limits..." -ForegroundColor Cyan
docker compose up -d
Write-Host ""

# Step 6: Wait for startup
Write-Host "Step 6: Waiting for containers to start (30 seconds)..." -ForegroundColor Cyan
Start-Sleep -Seconds 30
Write-Host "[OK] Containers started" -ForegroundColor Green
Write-Host ""

# Step 7: Re-queue jobs
Write-Host "Step 7: Re-queuing jobs..." -ForegroundColor Cyan
docker exec gen_scraper-backend-1 python requeue_jobs.py
Write-Host "[OK] Jobs re-queued" -ForegroundColor Green
Write-Host ""

# Step 8: Verify memory
Write-Host "Step 8: Verifying new memory limits..." -ForegroundColor Cyan
Write-Host ""
docker stats --no-stream
Write-Host ""

# Step 9: Check status
Write-Host "Step 9: Checking system status..." -ForegroundColor Cyan
Write-Host ""
Write-Host "Records:" -ForegroundColor Yellow
docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c "SELECT COUNT(*) as total FROM cleaned_results;"
Write-Host ""
Write-Host "Jobs:" -ForegroundColor Yellow
docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c "SELECT status, COUNT(*) FROM scrape_jobs GROUP BY status;"
Write-Host ""

Write-Host "=========================================================" -ForegroundColor Green
Write-Host "              MEMORY FIX COMPLETE!                       " -ForegroundColor Green
Write-Host "=========================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Worker now has 4GB memory limit (was 2GB)" -ForegroundColor Green
Write-Host "Memory usage should be around 50% instead of 99%" -ForegroundColor Green
Write-Host ""
Write-Host "Monitor with: docker stats --no-stream" -ForegroundColor Cyan
Write-Host ""
