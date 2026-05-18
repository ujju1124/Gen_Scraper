# Fix Merged Sources Array Bug
# Deduplicates the merged_from_sources array for records with corrupt data

Write-Host "🔧 Fixing merged_from_sources Array Bug..." -ForegroundColor Cyan
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

# Show records with corrupt merged_from_sources (more than 10 sources)
Write-Host "📊 Finding records with corrupt merged_from_sources arrays..." -ForegroundColor Yellow
Write-Host ""

$corruptQuery = @"
SELECT 
    name, 
    city, 
    array_length(merged_from_sources, 1) as source_count,
    merged_from_sources
FROM cleaned_results 
WHERE merged_from_sources IS NOT NULL 
AND array_length(merged_from_sources, 1) > 10
ORDER BY array_length(merged_from_sources, 1) DESC;
"@

docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c $corruptQuery

Write-Host ""
Write-Host "🔧 Fixing corrupt records by deduplicating merged_from_sources arrays..." -ForegroundColor Yellow
Write-Host ""

# Fix the corrupt records by deduplicating the array
$fixQuery = @"
UPDATE cleaned_results 
SET merged_from_sources = ARRAY(
    SELECT DISTINCT unnest(merged_from_sources) 
    ORDER BY 1
)
WHERE array_length(merged_from_sources, 1) > 10;
"@

docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c $fixQuery

Write-Host ""
Write-Host "✅ Fixed corrupt records" -ForegroundColor Green
Write-Host ""

# Show the fixed records
Write-Host "📊 Verifying fixed records..." -ForegroundColor Yellow
Write-Host ""

$verifyQuery = @"
SELECT 
    name, 
    city, 
    array_length(merged_from_sources, 1) as source_count,
    merged_from_sources
FROM cleaned_results 
WHERE name ILIKE '%thamel hub%'
OR name ILIKE '%nana yala%'
ORDER BY name;
"@

docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c $verifyQuery

Write-Host ""
Write-Host "📊 Checking actual cross-source merge statistics..." -ForegroundColor Yellow
Write-Host ""

# Count records with 2+ distinct sources
$statsQuery = @"
SELECT 
    COUNT(*) as total_cross_source_merges,
    AVG(array_length(merged_from_sources, 1)) as avg_sources_per_merge,
    MAX(array_length(merged_from_sources, 1)) as max_sources_per_merge
FROM cleaned_results 
WHERE merged_from_sources IS NOT NULL 
AND array_length(merged_from_sources, 1) >= 2;
"@

docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c $statsQuery

Write-Host ""
Write-Host "📊 Top 20 cross-source merges (after fix)..." -ForegroundColor Yellow
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
Write-Host "✅ Fix Complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Summary:" -ForegroundColor Cyan
Write-Host "- Fixed merged_from_sources arrays to contain only DISTINCT source IDs" -ForegroundColor White
Write-Host "- Updated backend/scrapers/merger.py to prevent future occurrences" -ForegroundColor White
Write-Host "- Verified cross-source merge statistics" -ForegroundColor White
Write-Host ""
Write-Host "Next: Re-run merge task to ensure all future merges use deduplicated arrays" -ForegroundColor Yellow
