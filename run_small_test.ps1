# Small Test Job for Booking.com Detail Page Scraping
# This script creates a minimal test job and monitors its progress

Write-Host "=== Booking.com Detail Page Scraping - Small Test ===" -ForegroundColor Cyan
Write-Host ""

# Step 1: Create test job in database
Write-Host "Step 1: Creating test job (max_results=1)..." -ForegroundColor Yellow
$jobIdRaw = docker-compose exec -T postgres psql -U scraper -d scraper_db -t -c "INSERT INTO scrape_jobs (id, user_id, category_id, location, source_ids, max_results, status, created_at) VALUES (gen_random_uuid(), 1, 1, 'Kathmandu', ARRAY[1], 1, 'QUEUED', NOW()) RETURNING id;"

# Extract just the UUID (first line, trimmed)
$jobId = ($jobIdRaw -split "`n")[0].Trim()

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to create job" -ForegroundColor Red
    exit 1
}

Write-Host "Job created: $jobId" -ForegroundColor Green
Write-Host ""

# Step 2: Trigger Celery task
Write-Host "Step 2: Triggering Celery task..." -ForegroundColor Yellow
docker-compose exec -T worker python -c "from tasks.scrape_task import scrape_task; task = scrape_task.delay('$jobId'); print(f'Task ID: {task.id}')"

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to trigger task" -ForegroundColor Red
    exit 1
}

Write-Host "Task triggered" -ForegroundColor Green
Write-Host ""

# Step 3: Monitor job progress
Write-Host "Step 3: Monitoring job progress (will check every 5 seconds for up to 2 minutes)..." -ForegroundColor Yellow
Write-Host ""

$maxAttempts = 24
$attempt = 0

while ($attempt -lt $maxAttempts) {
    $attempt++
    
    $status = docker-compose exec -T postgres psql -U scraper -d scraper_db -t -c "SELECT status FROM scrape_jobs WHERE id = '$jobId';" | ForEach-Object { $_.Trim() }
    
    Write-Host "[$attempt/$maxAttempts] Status: $status" -ForegroundColor Cyan
    
    if ($status -eq "DONE") {
        Write-Host ""
        Write-Host "Job completed successfully!" -ForegroundColor Green
        break
    }
    elseif ($status -eq "FAILED") {
        Write-Host ""
        Write-Host "Job failed!" -ForegroundColor Red
        
        $errorMsg = docker-compose exec -T postgres psql -U scraper -d scraper_db -t -c "SELECT error_message FROM scrape_jobs WHERE id = '$jobId';" | ForEach-Object { $_.Trim() }
        Write-Host "Error message: $errorMsg" -ForegroundColor Red
        break
    }
    
    Start-Sleep -Seconds 5
}

if ($attempt -ge $maxAttempts) {
    Write-Host ""
    Write-Host "Timeout: Job did not complete within 2 minutes" -ForegroundColor Yellow
    Write-Host "Current status: $status" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=== Results ===" -ForegroundColor Cyan
Write-Host ""

# Step 4: Check results
Write-Host "Step 4: Checking results..." -ForegroundColor Yellow
Write-Host ""

$resultCount = docker-compose exec -T postgres psql -U scraper -d scraper_db -t -c "SELECT COUNT(*) FROM cleaned_results WHERE job_id = '$jobId';" | ForEach-Object { $_.Trim() }
Write-Host "Total results: $resultCount" -ForegroundColor Cyan

if ([int]$resultCount -gt 0) {
    Write-Host ""
    Write-Host "Result details:" -ForegroundColor Cyan
    docker-compose exec -T postgres psql -U scraper -d scraper_db -c "SELECT name, address, rating_overall, amenities IS NOT NULL as has_amenities, checkin_time, checkout_time FROM cleaned_results WHERE job_id = '$jobId' AND source_id = 1 LIMIT 1;"
    
    Write-Host ""
    Write-Host "Checking detail page data..." -ForegroundColor Cyan
    docker-compose exec -T postgres psql -U scraper -d scraper_db -c "SELECT name, CASE WHEN amenities IS NOT NULL THEN jsonb_array_length(amenities) ELSE 0 END as amenity_count, checkin_time, checkout_time, description_short IS NOT NULL as has_description FROM cleaned_results WHERE job_id = '$jobId' AND source_id = 1 LIMIT 1;"
}

Write-Host ""
Write-Host "=== Recent Worker Logs ===" -ForegroundColor Cyan
Write-Host ""
docker-compose logs --tail=30 worker | Select-String -Pattern "booking_com|detail_page|amenities|checkin|completed" -Context 0,1

Write-Host ""
Write-Host "=== Test Complete ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Job ID: $jobId" -ForegroundColor White
Write-Host ""
Write-Host "To view full logs:" -ForegroundColor Gray
Write-Host "  docker-compose logs worker | Select-String -Pattern '$jobId'" -ForegroundColor Gray
Write-Host ""
Write-Host "To check job status:" -ForegroundColor Gray
Write-Host "  docker-compose exec -T postgres psql -U scraper -d scraper_db -c `"SELECT * FROM scrape_jobs WHERE id = '$jobId'`"" -ForegroundColor Gray
