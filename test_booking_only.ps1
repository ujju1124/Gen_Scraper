# Test Booking.com ONLY (no Google Maps) with max_results=1
# This reduces complexity and helps isolate the issue

Write-Host "=== Booking.com Only Test (No Google Maps) ===" -ForegroundColor Cyan
Write-Host ""

# Create job
Write-Host "Creating job (Booking.com only, max_results=1)..." -ForegroundColor Yellow
$jobIdRaw = docker-compose exec -T postgres psql -U scraper -d scraper_db -t -c "INSERT INTO scrape_jobs (id, user_id, category_id, location, source_ids, max_results, status, created_at) VALUES (gen_random_uuid(), 1, 1, 'Pokhara', ARRAY[1], 1, 'QUEUED', NOW()) RETURNING id;"
$jobId = ($jobIdRaw -split "`n")[0].Trim()

Write-Host "Job ID: $jobId" -ForegroundColor Green
Write-Host ""

# Trigger task
Write-Host "Triggering task..." -ForegroundColor Yellow
docker-compose exec -T worker python -c "from tasks.scrape_task import scrape_task; task = scrape_task.delay('$jobId'); print(f'Task ID: {task.id}')"
Write-Host ""

# Monitor for 3 minutes
Write-Host "Monitoring (checking every 5 seconds for 3 minutes)..." -ForegroundColor Yellow
Write-Host ""

$maxAttempts = 36
$attempt = 0

while ($attempt -lt $maxAttempts) {
    $attempt++
    
    $status = docker-compose exec -T postgres psql -U scraper -d scraper_db -t -c "SELECT status FROM scrape_jobs WHERE id = '$jobId';" | ForEach-Object { $_.Trim() }
    
    $timestamp = Get-Date -Format "HH:mm:ss"
    Write-Host "[$timestamp] [$attempt/$maxAttempts] Status: $status" -ForegroundColor Cyan
    
    if ($status -eq "DONE") {
        Write-Host ""
        Write-Host "SUCCESS! Job completed" -ForegroundColor Green
        break
    }
    elseif ($status -eq "FAILED") {
        Write-Host ""
        Write-Host "Job failed" -ForegroundColor Red
        $errorMsg = docker-compose exec -T postgres psql -U scraper -d scraper_db -t -c "SELECT error_message FROM scrape_jobs WHERE id = '$jobId';" | ForEach-Object { $_.Trim() }
        Write-Host "Error: $errorMsg" -ForegroundColor Red
        break
    }
    
    Start-Sleep -Seconds 5
}

if ($attempt -ge $maxAttempts) {
    Write-Host ""
    Write-Host "Timeout after 3 minutes" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=== Results ===" -ForegroundColor Cyan
Write-Host ""

# Check results
$resultCount = docker-compose exec -T postgres psql -U scraper -d scraper_db -t -c "SELECT COUNT(*) FROM cleaned_results WHERE job_id = '$jobId';" | ForEach-Object { $_.Trim() }
Write-Host "Total results: $resultCount" -ForegroundColor White

if ([int]$resultCount -gt 0) {
    Write-Host ""
    Write-Host "Result data:" -ForegroundColor Cyan
    docker-compose exec -T postgres psql -U scraper -d scraper_db -c "SELECT name, address, rating_overall, CASE WHEN amenities IS NOT NULL THEN jsonb_array_length(amenities) ELSE 0 END as amenity_count, checkin_time, checkout_time FROM cleaned_results WHERE job_id = '$jobId' AND source_id = 1 LIMIT 1;"
}

Write-Host ""
Write-Host "=== Worker Logs (last 50 lines) ===" -ForegroundColor Cyan
docker-compose logs --tail=50 worker | Select-String -Pattern "$jobId|booking_com|detail|completed|timeout|error" -Context 0,1

Write-Host ""
Write-Host "Job ID: $jobId" -ForegroundColor Gray
