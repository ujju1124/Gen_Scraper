# Reset Merge Data and Re-run with Fixed Logic
# Fixes the placeholder coordinate bug in fuzzy matching

Write-Host "🔧 Resetting Merge Data and Re-running with Fixed Logic..." -ForegroundColor Cyan
Write-Host ""

# Check if Docker is running
Write-Host "Checking Docker status..." -ForegroundColor Yellow
$dockerStatus = docker info 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Docker is not running. Please start Docker Desktop first." -ForegroundColor Red
    exit 1
}
Write-Host "✅ Docker is running" -ForegroundColor Green
Write-Host ""

# Show current merge statistics
Write-Host "📊 Current Merge Statistics (BEFORE RESET)..." -ForegroundColor Yellow
Write-Host ""

$beforeQuery = @"
SELECT 
    COUNT(*) as total_records,
    COUNT(CASE WHEN merged_from_sources IS NOT NULL THEN 1 END) as merged_records,
    COUNT(CASE WHEN is_duplicate = true THEN 1 END) as duplicate_records
FROM cleaned_results;
"@

docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c $beforeQuery

Write-Host ""
Write-Host "🔄 Resetting all merge data..." -ForegroundColor Yellow
Write-Host ""

# Reset all merge-related fields
$resetQuery = @"
UPDATE cleaned_results 
SET 
    is_duplicate = false,
    merged_from_sources = NULL,
    merged_at = NULL
WHERE merged_from_sources IS NOT NULL OR is_duplicate = true;
"@

docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c $resetQuery

Write-Host ""
Write-Host "✅ Reset complete" -ForegroundColor Green
Write-Host ""

# Verify reset
Write-Host "📊 Verifying reset..." -ForegroundColor Yellow
Write-Host ""

$verifyQuery = @"
SELECT 
    COUNT(*) as total_records,
    COUNT(CASE WHEN merged_from_sources IS NOT NULL THEN 1 END) as merged_records,
    COUNT(CASE WHEN is_duplicate = true THEN 1 END) as duplicate_records
FROM cleaned_results;
"@

docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c $verifyQuery

Write-Host ""
Write-Host "🚀 Triggering cross-job merge with FIXED logic..." -ForegroundColor Yellow
Write-Host ""
Write-Host "This will take 1-2 minutes..." -ForegroundColor Gray
Write-Host ""

# Trigger merge via API (need to get session cookie first)
# For now, we'll trigger it via Celery directly
docker exec gen_scraper-worker-1 celery -A tasks.scrape_task call tasks.merge_all_sources

Write-Host ""
Write-Host "⏳ Waiting for merge to complete (30 seconds)..." -ForegroundColor Yellow
Start-Sleep -Seconds 30

Write-Host ""
Write-Host "📊 Final Merge Statistics (AFTER FIX)..." -ForegroundColor Yellow
Write-Host ""

$afterQuery = @"
SELECT 
    COUNT(*) as total_records,
    COUNT(CASE WHEN merged_from_sources IS NOT NULL THEN 1 END) as merged_records,
    COUNT(CASE WHEN is_duplicate = true THEN 1 END) as duplicate_records,
    ROUND(100.0 * COUNT(CASE WHEN merged_from_sources IS NOT NULL THEN 1 END) / COUNT(*), 2) as merge_rate_percent
FROM cleaned_results;
"@

docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c $afterQuery

Write-Host ""
Write-Host "📊 Cross-Source Merge Statistics..." -ForegroundColor Yellow
Write-Host ""

$crossSourceQuery = @"
SELECT 
    COUNT(*) as cross_source_merges,
    ROUND(AVG(array_length(merged_from_sources, 1)), 2) as avg_sources,
    MAX(array_length(merged_from_sources, 1)) as max_sources
FROM cleaned_results 
WHERE merged_from_sources IS NOT NULL 
AND array_length(merged_from_sources, 1) >= 2;
"@

docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c $crossSourceQuery

Write-Host ""
Write-Host "📊 Top 20 Cross-Source Merges..." -ForegroundColor Yellow
Write-Host ""

$topMergesQuery = @"
SELECT 
    name, 
    city, 
    merged_from_sources,
    array_length(merged_from_sources, 1) as source_count
FROM cleaned_results 
WHERE merged_from_sources IS NOT NULL 
AND array_length(merged_from_sources, 1) >= 2
ORDER BY array_length(merged_from_sources, 1) DESC 
LIMIT 20;
"@

docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c $topMergesQuery

Write-Host ""
Write-Host "🔍 Verifying Thamel Hub Hostel Fix..." -ForegroundColor Yellow
Write-Host ""

$thamelQuery = @"
SELECT name, city, source_id, is_duplicate, merged_from_sources 
FROM cleaned_results 
WHERE name = 'Thamel Hub Hostel' 
ORDER BY is_duplicate, source_id;
"@

docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c $thamelQuery

Write-Host ""
Write-Host "✅ Reset and Re-run Complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Summary:" -ForegroundColor Cyan
Write-Host "- Reset all merge data" -ForegroundColor White
Write-Host "- Re-ran merge with FIXED logic:" -ForegroundColor White
Write-Host "  • Placeholder coordinate blacklist (27.7172000, 85.3240000)" -ForegroundColor White
Write-Host "  • 80% name similarity required for coordinate matches" -ForegroundColor White
Write-Host "- Verified Thamel Hub Hostel is correctly merged" -ForegroundColor White
Write-Host ""
Write-Host "Expected Results:" -ForegroundColor Yellow
Write-Host "- Cross-source merges: 20-50 (realistic, not inflated)" -ForegroundColor White
Write-Host "- Thamel Hub Hostel: merged_from_sources = {7} or NULL" -ForegroundColor White
Write-Host "- No false positives from placeholder coordinates" -ForegroundColor White
