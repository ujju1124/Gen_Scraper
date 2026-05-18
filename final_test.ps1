# Final test with Kathmandu location
Write-Host "=== Final Test: Booking.com Detail Page Scraping ===" -ForegroundColor Cyan
Write-Host ""

# Create job for Kathmandu
Write-Host "Creating job (Kathmandu, Booking.com only, max_results=1)..." -ForegroundColor Yellow
$jobIdRaw = docker-compose exec -T postgres psql -U scraper -d scraper_db -t -c "INSERT INTO scrape_jobs (id, user_id, category_id, location, source_ids, max_results, status, created_at) VALUES (gen_random_uuid(), 1, 1, 'Kathmandu', ARRAY[1], 1, 'QUEUED', NOW()) RETURNING id;"
$jobId = ($jobIdRaw -split "`n")[0].Trim()

Write-Host "Job ID: $jobId" -ForegroundColor Green
Write-Host ""

# Trigger task
docker-compose exec -T worker python -c "from tasks.scrape_task import scrape_task; task = scrape_task.delay('$jobId'); print(f'Triggered')"
Write-Host ""

# Monitor
Write-Host "Monitoring..." -ForegroundColor Yellow
$maxAttempts = 40
$attempt = 0

while ($attempt -lt $maxAttempts) {
    $attempt++
    $status = docker-compose exec -T postgres psql -U scraper -d scraper_db -t -c "SELECT status FROM scrape_jobs WHERE id = '$jobId';" | ForEach-Object { $_.Trim() }
    
    Write-Host "[$attempt/$maxAttempts] $status" -ForegroundColor Cyan
    
    if ($status -eq "DONE") {
        Write-Host ""
        Write-Host "SUCCESS!" -ForegroundColor Green
        break
    }
    elseif ($status -eq "FAILED") {
        Write-Host ""
        Write-Host "FAILED" -ForegroundColor Red
        break
    }
    
    Start-Sleep -Seconds 5
}

Write-Host ""
Write-Host "=== Results ===" -ForegroundColor Cyan

# Get Booking.com results
$bookingResults = docker-compose exec -T postgres psql -U scraper -d scraper_db -t -c "SELECT COUNT(*) FROM cleaned_results WHERE job_id = '$jobId' AND source_id = 1;" | ForEach-Object { $_.Trim() }
Write-Host "Booking.com results: $bookingResults" -ForegroundColor White

if ($bookingResults -match '\d+' -and [int]$bookingResults -gt 0) {
    Write-Host ""
    Write-Host "Detail page data:" -ForegroundColor Cyan
    docker-compose exec -T postgres psql -U scraper -d scraper_db -c "SELECT name, CASE WHEN amenities IS NOT NULL THEN jsonb_array_length(amenities) ELSE 0 END as amenities_count, checkin_time, checkout_time FROM cleaned_results WHERE job_id = '$jobId' AND source_id = 1 LIMIT 1;"
    
    Write-Host ""
    Write-Host "Checking if detail page was visited..." -ForegroundColor Cyan
    docker-compose logs worker 2>&1 | Select-String -Pattern "$jobId.*detail_urls_collected|$jobId.*extracting_detail|$jobId.*starting_detail" | Select-Object -Last 5
}

Write-Host ""
Write-Host "Job ID: $jobId" -ForegroundColor Gray
