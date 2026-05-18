-- Scale Test Suite: Break 5 selectors and verify healing
-- Target: 4/5 or 5/5 tests pass (80-100% success rate)

-- ============================================================
-- TEST #1: Booking.com Name Selector
-- ============================================================
UPDATE scraper_selectors 
SET selector = '[data-testid=FINAL_TEST_1_BOOKING_NAME]'
WHERE source_id = 1 AND field_name = 'name';

SELECT 'TEST #1: Booking.com name selector broken' AS status;

-- ============================================================
-- TEST #2: NepalYP Name Selector
-- ============================================================
UPDATE scraper_selectors 
SET selector = '[data-testid=FINAL_TEST_2_NEPALYP_NAME]'
WHERE source_id IN (SELECT id FROM sources WHERE name = 'nepalyp_banks') 
AND field_name = 'name';

SELECT 'TEST #2: NepalYP name selector broken' AS status;

-- ============================================================
-- TEST #3: Google Maps Rating Selector
-- ============================================================
UPDATE scraper_selectors 
SET selector = '[data-testid=FINAL_TEST_3_GMAPS_RATING]'
WHERE source_id IN (SELECT id FROM sources WHERE name = 'google_maps') 
AND field_name = 'rating';

SELECT 'TEST #3: Google Maps rating selector broken' AS status;

-- ============================================================
-- TEST #4: Booking.com Address Selector
-- ============================================================
UPDATE scraper_selectors 
SET selector = '[data-testid=FINAL_TEST_4_BOOKING_ADDRESS]'
WHERE source_id = 1 AND field_name = 'address';

SELECT 'TEST #4: Booking.com address selector broken' AS status;

-- ============================================================
-- TEST #5: NepalYP Phone Selector
-- ============================================================
UPDATE scraper_selectors 
SET selector = '[data-testid=FINAL_TEST_5_NEPALYP_PHONE]'
WHERE source_id IN (SELECT id FROM sources WHERE name = 'nepalyp_banks') 
AND field_name = 'phone';

SELECT 'TEST #5: NepalYP phone selector broken' AS status;

-- ============================================================
-- VERIFICATION: Show all broken selectors
-- ============================================================
SELECT 
    s.name AS source_name,
    ss.field_name,
    ss.selector
FROM scraper_selectors ss
JOIN sources s ON ss.source_id = s.id
WHERE ss.selector LIKE '%FINAL_TEST%'
ORDER BY ss.selector;

SELECT '✅ All 5 selectors broken - ready for scale testing' AS final_status;
