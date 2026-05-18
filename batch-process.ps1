# Batch Processing Script
# Process jobs in controlled 10-minute batches

param(
    [Parameter(Mandatory=$false)]
    [int]$BatchNumber = 1,
    
    [Parameter(Mandatory=$false)]
    [int]$DurationMinutes = 10
)

Write-Host ""
Write-Host "=========================================================" -ForegroundColor Cyan
Write-Host "        BATCH $BatchNumber PROCESSING                    " -ForegroundColor Cyan
Write-Host "=========================================================" -ForegroundColor Cyan
Write-Host ""

# Check current status
Write-Host "Current Status:" -ForegroundColor Yellow
docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c "SELECT COUNT(*) as records FROM cleaned_results; SELECT status, COUNT(*) FROM scrape_jobs GROUP BY status ORDER BY status;"
Write-Host ""

# Re-queue jobs
Write-Host "Re-queuing jobs..." -ForegroundColor Cyan
docker exec gen_scraper-backend-1 python requeue_jobs.py
Write-Host ""

# Start worker
Write-Host "Starting worker for $DurationMinutes minutes..." -ForegroundColor Green
docker compose start worker
Write-Host ""

# Show initial memory
Write-Host "Initial Memory:" -ForegroundColor Yellow
docker stats --no-stream gen_scraper-worker-1
Write-Host ""

# Calculate end time
$endTime = (Get-Date).AddMinutes($DurationMinutes)
Write-Host "Batch will run until: $($endTime.ToString('HH:mm:ss'))" -ForegroundColor Yellow
Write-Host ""

# Monitor progress
$checkInterval = 2 # Check every 2 minutes
$checksRemaining = [math]::Ceiling($DurationMinutes / $checkInterval)

for ($i = 1; $i -le $checksRemaining; $i++) {
    $minutesElapsed = $i * $checkInterval
    if ($minutesElapsed -gt $DurationMinutes) {
        $minutesElapsed = $DurationMinutes
    }
    
    Write-Host "[$minutesElapsed/$DurationMinutes minutes] Checking progress..." -ForegroundColor Cyan
    
    # Check memory
    docker stats --no-stream gen_scraper-worker-1 | Select-Object -Last 1
    
    # Check job progress
    $result = docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -t -c "SELECT COUNT(*) FROM scrape_jobs WHERE status='DONE';"
    $jobsDone = $result.Trim()
    Write-Host "  Jobs completed: $jobsDone" -ForegroundColor White
    
    Write-Host ""
    
    # Sleep until next check or end
    if ($i -lt $checksRemaining) {
        $sleepSeconds = $checkInterval * 60
        if (($i * $checkInterval) + $checkInterval -gt $DurationMinutes) {
            $sleepSeconds = ($DurationMinutes - ($i * $checkInterval)) * 60
        }
        Start-Sleep -Seconds $sleepSeconds
    }
}

# Stop worker
Write-Host ""
Write-Host "Stopping worker..." -ForegroundColor Yellow
docker compose stop worker
Write-Host ""

# Final status
Write-Host "Batch $BatchNumber Complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Final Status:" -ForegroundColor Yellow
docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c "SELECT COUNT(*) as records FROM cleaned_results; SELECT status, COUNT(*) FROM scrape_jobs GROUP BY status ORDER BY status;"
Write-Host ""

Write-Host "=========================================================" -ForegroundColor Green
Write-Host "        BATCH $BatchNumber FINISHED                      " -ForegroundColor Green
Write-Host "=========================================================" -ForegroundColor Green
Write-Host ""

if ($BatchNumber -eq 1) {
    Write-Host "Wait 5 minutes for cool down, then run:" -ForegroundColor Cyan
    Write-Host "  .\batch-process.ps1 -BatchNumber 2" -ForegroundColor White
    Write-Host ""
}
