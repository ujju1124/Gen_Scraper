# Diagnose Merge Rate Bug
# Run this after Docker Desktop is started

Write-Host ""
Write-Host "=========================================================" -ForegroundColor Cyan
Write-Host "        DIAGNOSING MERGE RATE BUG                        " -ForegroundColor Cyan
Write-Host "=========================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Expected: 15-20% merge rate (720-960 merged records)" -ForegroundColor Yellow
Write-Host "Actual: 0.25% merge rate (12 merged records)" -ForegroundColor Red
Write-Host ""

# Check if Docker is running
Write-Host "Checking Docker status..." -ForegroundColor Cyan
try {
    docker ps | Out-Null
    Write-Host "[OK] Docker is running" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Docker is not running!" -ForegroundColor Red
    Write-Host "Please start Docker Desktop first, then run this script again." -ForegroundColor Yellow
    exit 1
}
Write-Host ""

# Step 1: Check for duplicate hotel names
Write-Host "=========================================================" -ForegroundColor Cyan
Write-Host "STEP 1: Checking for duplicate hotel names in DB" -ForegroundColor Cyan
Write-Host "=========================================================" -ForegroundColor Cyan
Write-Host ""
docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c "SELECT name, city, COUNT(*) as count FROM cleaned_results GROUP BY name, city HAVING COUNT(*) > 1 ORDER BY count DESC LIMIT 20;"
Write-Host ""

# Step 2: Check if dedup_key is consistent
Write-Host "=========================================================" -ForegroundColor Cyan
Write-Host "STEP 2: Checking dedup_key consistency across sources" -ForegroundColor Cyan
Write-Host "=========================================================" -ForegroundColor Cyan
Write-Host ""
docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c "SELECT name, city, dedup_key, source_id, is_duplicate FROM cleaned_results WHERE name ILIKE '%barahi%' OR name ILIKE '%himalaya%' OR name ILIKE '%everest%' ORDER BY name, city;"
Write-Host ""

# Step 3: Check merger run history
Write-Host "=========================================================" -ForegroundColor Cyan
Write-Host "STEP 3: Checking merger run history by job" -ForegroundColor Cyan
Write-Host "=========================================================" -ForegroundColor Cyan
Write-Host ""
docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c "SELECT job_id, COUNT(*) as records, COUNT(CASE WHEN merged_from_sources IS NOT NULL THEN 1 END) as merged, COUNT(CASE WHEN is_duplicate = TRUE THEN 1 END) as duplicates FROM cleaned_results GROUP BY job_id ORDER BY job_id DESC LIMIT 10;"
Write-Host ""

# Step 4: Check if MergingPipeline is being called
Write-Host "=========================================================" -ForegroundColor Cyan
Write-Host "STEP 4: Checking worker logs for merging activity" -ForegroundColor Cyan
Write-Host "=========================================================" -ForegroundColor Cyan
Write-Host ""
docker logs gen_scraper-worker-1 --tail=200 | Select-String -Pattern "merger|merging|merged_groups" -CaseSensitive:$false
Write-Host ""

# Summary
Write-Host "=========================================================" -ForegroundColor Yellow
Write-Host "DIAGNOSIS COMPLETE" -ForegroundColor Yellow
Write-Host "=========================================================" -ForegroundColor Yellow
Write-Host ""
Write-Host "Analyze the output above to identify:" -ForegroundColor Yellow
Write-Host "1. Are there duplicate names that should be merged?" -ForegroundColor White
Write-Host "2. Do different sources have different dedup_keys for same business?" -ForegroundColor White
Write-Host "3. Is merging only happening within single jobs?" -ForegroundColor White
Write-Host "4. Is MergingPipeline being called at all?" -ForegroundColor White
Write-Host ""
Write-Host "Save this output and share with supervisor for analysis." -ForegroundColor Cyan
Write-Host ""
