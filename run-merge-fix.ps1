# Run Cross-Job Merge Fix
# This script triggers the merge task to fix the 0.25% merge rate bug

Write-Host ""
Write-Host "=========================================================" -ForegroundColor Cyan
Write-Host "        RUNNING CROSS-JOB MERGE FIX" -ForegroundColor Cyan
Write-Host "=========================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "This will merge records from different sources that represent" -ForegroundColor Yellow
Write-Host "the same business (e.g., Hotel Barahi from Booking.com + Google Maps)" -ForegroundColor Yellow
Write-Host ""
Write-Host "Expected merge rate: 15-20% (720-960 merged records)" -ForegroundColor Green
Write-Host ""

# Check if Docker is running
Write-Host "Checking Docker status..." -ForegroundColor Cyan
$dockerStatus = docker info 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Docker is not running!" -ForegroundColor Red
    Write-Host "Please start Docker Desktop and try again." -ForegroundColor Yellow
    exit 1
}
Write-Host "[OK] Docker is running" -ForegroundColor Green
Write-Host ""

# Check merge rate BEFORE fix
Write-Host "=========================================================" -ForegroundColor Cyan
Write-Host "MERGE RATE BEFORE FIX" -ForegroundColor Cyan
Write-Host "=========================================================" -ForegroundColor Cyan
Write-Host ""

docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c "SELECT COUNT(*) as total, COUNT(CASE WHEN merged_from_sources IS NOT NULL THEN 1 END) as merged, ROUND(100.0 * COUNT(CASE WHEN merged_from_sources IS NOT NULL THEN 1 END) / COUNT(*), 2) as merge_rate_percent FROM cleaned_results;"

Write-Host ""
Write-Host "=========================================================" -ForegroundColor Cyan
Write-Host "RUNNING MERGE TASK" -ForegroundColor Cyan
Write-Host "=========================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "This may take 2-5 minutes for 4,790 records..." -ForegroundColor Yellow
Write-Host ""

# Run merge task directly in backend container
docker exec gen_scraper-backend-1 python -c "from tasks.merge_task import merge_all_sources; from database import SessionLocal; from tasks.merge_task import CrossJobMergingPipeline; db = SessionLocal(); pipeline = CrossJobMergingPipeline(db); stats = pipeline.run(); print(''); print('=' * 60); print('MERGE COMPLETE'); print('=' * 60); print('Total Records Processed:', stats['total_records_processed']); print('Exact Merged Groups:', stats['exact_merged_groups']); print('Exact Merged Records:', stats['exact_merged_records']); print('Fuzzy Merged Groups:', stats['fuzzy_merged_groups']); print('Fuzzy Merged Records:', stats['fuzzy_merged_records']); print('Total Merged Groups:', stats['total_merged_groups']); print('Total Merged Records:', stats['total_merged_records']); print('Merge Rate:', str(stats['merge_rate_percent']) + '%'); print('=' * 60); db.close()"

Write-Host ""
Write-Host "=========================================================" -ForegroundColor Cyan
Write-Host "MERGE RATE AFTER FIX" -ForegroundColor Cyan
Write-Host "=========================================================" -ForegroundColor Cyan
Write-Host ""

docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c "SELECT COUNT(*) as total, COUNT(CASE WHEN merged_from_sources IS NOT NULL THEN 1 END) as merged, ROUND(100.0 * COUNT(CASE WHEN merged_from_sources IS NOT NULL THEN 1 END) / COUNT(*), 2) as merge_rate_percent FROM cleaned_results;"

Write-Host ""
Write-Host "=========================================================" -ForegroundColor Cyan
Write-Host "VERIFICATION: Check specific hotels" -ForegroundColor Cyan
Write-Host "=========================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Checking Hotel Barahi (should be merged from multiple sources):" -ForegroundColor Yellow
Write-Host ""

docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c "SELECT name, city, source_id, is_duplicate, merged_from_sources FROM cleaned_results WHERE name ILIKE '%barahi%' ORDER BY name, is_duplicate;"

Write-Host ""
Write-Host "=========================================================" -ForegroundColor Cyan
Write-Host "FIX COMPLETE" -ForegroundColor Cyan
Write-Host "=========================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "If merge rate is now 15-20%, the fix was successful!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Run full test suite: docker-compose run --rm backend pytest" -ForegroundColor White
Write-Host "2. Check frontend to verify merged records display correctly" -ForegroundColor White
Write-Host "3. Proceed to Task 3 (Test Selector Healing System)" -ForegroundColor White
Write-Host ""
