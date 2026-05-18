# Test script for Booking.com detail page scraping
# PowerShell version for Windows

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "Booking.com Detail Scraping Test" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Apply database selectors
Write-Host "Step 1: Applying database selectors..." -ForegroundColor Yellow
docker cp add_booking_detail_selectors.sql gen_scraper-postgres-1:/tmp/
docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -f /tmp/add_booking_detail_selectors.sql
Write-Host "✓ Selectors applied" -ForegroundColor Green
Write-Host ""

# Step 2: Restart services
Write-Host "Step 2: Restarting backend and celery..." -ForegroundColor Yellow
docker-compose restart backend celery
Write-Host "✓ Services restarted" -ForegroundColor Green
Write-Host ""

# Step 3: Wait for services to be ready
Write-Host "Step 3: Waiting for services to be ready (30 seconds)..." -ForegroundColor Yellow
Start-Sleep -Seconds 30
Write-Host "✓ Services ready" -ForegroundColor Green
Write-Host ""

# Step 4: Check if selectors were added
Write-Host "Step 4: Verifying selectors in database..." -ForegroundColor Yellow
docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c "SELECT COUNT(*) as detail_selector_count FROM scraper_selectors WHERE source_id = 1 AND field_name LIKE 'detail_%';"
Write-Host ""

# Step 5: Instructions for manual testing
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "Manual Testing Steps:" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Open admin panel: http://localhost:5173" -ForegroundColor White
Write-Host "2. Create a new scrape job:" -ForegroundColor White
Write-Host "   - Source: Booking.com" -ForegroundColor Gray
Write-Host "   - Location: Kathmandu" -ForegroundColor Gray
Write-Host "   - Max Results: 5" -ForegroundColor Gray
Write-Host "   - Category: Hotels" -ForegroundColor Gray
Write-Host ""
Write-Host "3. Wait for job to complete (check status)" -ForegroundColor White
Write-Host ""
Write-Host "4. Run verification query:" -ForegroundColor White
Write-Host '   docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c "SELECT name, amenities IS NOT NULL as has_amenities, review_scores IS NOT NULL as has_review_scores, checkin_time, checkout_time, languages FROM cleaned_results WHERE source_id = 1 ORDER BY created_at DESC LIMIT 5;"' -ForegroundColor Gray
Write-Host ""
Write-Host "5. Check logs for detail extraction:" -ForegroundColor White
Write-Host "   docker logs gen_scraper-celery-1 --tail 100 | Select-String 'detail'" -ForegroundColor Gray
Write-Host ""
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "Expected Results:" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "- has_amenities: true for 3+ records" -ForegroundColor White
Write-Host "- has_review_scores: true for 3+ records" -ForegroundColor White
Write-Host "- checkin_time: 'From 14:00 to 23:30' or similar" -ForegroundColor White
Write-Host "- checkout_time: 'Until 12:00' or similar" -ForegroundColor White
Write-Host "- languages: 'Hindi' or similar" -ForegroundColor White
Write-Host ""
