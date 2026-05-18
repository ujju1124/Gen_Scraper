#!/bin/bash
# Test script for Booking.com detail page scraping

echo "========================================="
echo "Booking.com Detail Scraping Test"
echo "========================================="
echo ""

# Step 1: Apply database selectors
echo "Step 1: Applying database selectors..."
docker cp add_booking_detail_selectors.sql gen_scraper-postgres-1:/tmp/
docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -f /tmp/add_booking_detail_selectors.sql
echo "✓ Selectors applied"
echo ""

# Step 2: Restart services
echo "Step 2: Restarting backend and celery..."
docker-compose restart backend celery
echo "✓ Services restarted"
echo ""

# Step 3: Wait for services to be ready
echo "Step 3: Waiting for services to be ready (30 seconds)..."
sleep 30
echo "✓ Services ready"
echo ""

# Step 4: Check if selectors were added
echo "Step 4: Verifying selectors in database..."
docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c "
SELECT COUNT(*) as detail_selector_count
FROM scraper_selectors 
WHERE source_id = 1 AND field_name LIKE 'detail_%';
"
echo ""

# Step 5: Instructions for manual testing
echo "========================================="
echo "Manual Testing Steps:"
echo "========================================="
echo ""
echo "1. Open admin panel: http://localhost:5173"
echo "2. Create a new scrape job:"
echo "   - Source: Booking.com"
echo "   - Location: Kathmandu"
echo "   - Max Results: 5"
echo "   - Category: Hotels"
echo ""
echo "3. Wait for job to complete (check status)"
echo ""
echo "4. Run verification query:"
echo "   docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c \""
echo "   SELECT "
echo "       name,"
echo "       amenities IS NOT NULL as has_amenities,"
echo "       review_scores IS NOT NULL as has_review_scores,"
echo "       checkin_time,"
echo "       checkout_time,"
echo "       languages"
echo "   FROM cleaned_results "
echo "   WHERE source_id = 1 "
echo "   ORDER BY created_at DESC "
echo "   LIMIT 5;"
echo "   \""
echo ""
echo "5. Check logs for detail extraction:"
echo "   docker logs gen_scraper-celery-1 --tail 100 | grep detail"
echo ""
echo "========================================="
echo "Expected Results:"
echo "========================================="
echo "- has_amenities: true for 3+ records"
echo "- has_review_scores: true for 3+ records"
echo "- checkin_time: 'From 14:00 to 23:30' or similar"
echo "- checkout_time: 'Until 12:00' or similar"
echo "- languages: 'Hindi' or similar"
echo ""
