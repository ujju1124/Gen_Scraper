# City Expansion Monitoring Script
# Run this to monitor progress every 30 seconds

Write-Host "=== City Expansion Monitor ===" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop monitoring" -ForegroundColor Yellow
Write-Host ""

$startTime = Get-Date
$lastResultCount = 0

while ($true) {
    $currentTime = Get-Date
    $elapsed = $currentTime - $startTime
    
    Write-Host "[$($currentTime.ToString('HH:mm:ss'))] Checking status... (Elapsed: $($elapsed.ToString('hh\:mm\:ss')))" -ForegroundColor Cyan
    
    # Check Docker status
    $dockerStatus = docker info 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Docker is disconnected!" -ForegroundColor Red
        Write-Host "Run docker-emergency-recovery.ps1 to recover" -ForegroundColor Yellow
        break
    }
    
    # Check job queue
    Write-Host "`nJob Queue:" -ForegroundColor Green
    docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c "SELECT status, COUNT(*) FROM scrape_jobs WHERE status != 'CANCELLED' GROUP BY status ORDER BY status;" 2>$null
    
    # Check total results
    Write-Host "`nTotal Results:" -ForegroundColor Green
    $resultOutput = docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -t -c "SELECT COUNT(*) FROM cleaned_results;" 2>$null
    $currentResultCount = [int]($resultOutput.Trim())
    
    if ($lastResultCount -gt 0) {
        $newResults = $currentResultCount - $lastResultCount
        $progressPercent = [math]::Round(($currentResultCount / 7000) * 100, 1)
        Write-Host "Current: $currentResultCount / 7,000 ($progressPercent%)" -ForegroundColor White
        Write-Host "New results since last check: +$newResults" -ForegroundColor $(if ($newResults -gt 0) { "Green" } else { "Yellow" })
    } else {
        Write-Host "Current: $currentResultCount / 7,000" -ForegroundColor White
    }
    
    $lastResultCount = $currentResultCount
    
    # Check if target reached
    if ($currentResultCount -ge 7000) {
        Write-Host "`n🎉 Target reached! $currentResultCount results collected!" -ForegroundColor Green
        Write-Host "`nFinal city distribution:" -ForegroundColor Cyan
        docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c "SELECT city, COUNT(*) as count FROM cleaned_results GROUP BY city ORDER BY COUNT(*) DESC LIMIT 15;" 2>$null
        break
    }
    
    # Check city expansion progress
    Write-Host "`nCity Expansion Jobs (Running/Queued):" -ForegroundColor Green
    docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c "SELECT c.name as category, s.name as source, sj.location, sj.status FROM scrape_jobs sj JOIN categories c ON sj.category_id = c.id JOIN sources s ON s.id = ANY(sj.source_ids) WHERE sj.status IN ('RUNNING', 'QUEUED') AND sj.created_at > NOW() - INTERVAL '2 hours' ORDER BY sj.status, sj.created_at LIMIT 10;" 2>$null
    
    Write-Host "`n" + ("=" * 80) -ForegroundColor DarkGray
    Write-Host "Next check in 30 seconds..." -ForegroundColor DarkGray
    Write-Host ""
    
    Start-Sleep -Seconds 30
}

Write-Host "`nMonitoring stopped." -ForegroundColor Yellow
