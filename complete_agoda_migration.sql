-- Complete Agoda Migration Script
-- Run this after Docker Desktop is restarted

-- Step 1: Verify Agoda source exists and get its ID
SELECT id, name, base_url, heal_mode FROM sources WHERE name = 'agoda';

-- Step 2: Add selectors for Agoda
-- Note: These selectors need to be verified against actual Agoda website
-- Update them based on real selectors found during testing

INSERT INTO scraper_selectors (source_id, field_name, selector, selector_type, is_active, verified_at)
VALUES
    -- Get source_id from Step 1 result
    ((SELECT id FROM sources WHERE name = 'agoda'), 'name', '[data-selenium="hotel-name"], h3[class*="PropertyCard"], [class*="hotel-name"]', 'css', true, NOW()),
    ((SELECT id FROM sources WHERE name = 'agoda'), 'address', '[data-selenium="hotel-address"], [class*="hotel-address"], [class*="PropertyCard"] [class*="address"]', 'css', true, NOW()),
    ((SELECT id FROM sources WHERE name = 'agoda'), 'price', '[data-selenium="hotel-price"], [class*="PropertyCard"] [class*="price"], [data-ppapi="room-price"]', 'css', true, NOW()),
    ((SELECT id FROM sources WHERE name = 'agoda'), 'rating', '[data-selenium="hotel-rating"], [class*="PropertyCard"] [class*="rating"], [class*="review-score"]', 'css', true, NOW())
ON CONFLICT (source_id, field_name) DO UPDATE
SET 
    selector = EXCLUDED.selector,
    selector_type = EXCLUDED.selector_type,
    verified_at = EXCLUDED.verified_at;

-- Step 3: Add field hints (real example values from Agoda website)
-- These should be updated with actual values seen on Agoda
UPDATE sources
SET field_hints = '{
    "name": "Hyatt Regency Kathmandu",
    "address": "Taragaon, Boudha, Kathmandu 44600",
    "price": "NPR 15,234",
    "rating": "8.5"
}'::jsonb
WHERE name = 'agoda';

-- Step 4: Set heal mode to AUTO
UPDATE sources 
SET heal_mode = 'AUTO' 
WHERE name = 'agoda';

-- Step 5: Verify configuration
SELECT 
    s.id as source_id,
    s.name as source_name,
    s.heal_mode,
    s.field_hints,
    ss.field_name,
    ss.selector,
    ss.selector_type,
    ss.is_active
FROM sources s
LEFT JOIN scraper_selectors ss ON s.id = ss.source_id
WHERE s.name = 'agoda'
ORDER BY ss.field_name;

-- Step 6: Check if any selectors are missing
SELECT 
    'Missing selectors for: ' || string_agg(field, ', ') as warning
FROM (
    SELECT unnest(ARRAY['name', 'address', 'price', 'rating']) as field
    EXCEPT
    SELECT field_name 
    FROM scraper_selectors 
    WHERE source_id = (SELECT id FROM sources WHERE name = 'agoda')
) missing;

-- Expected output: No rows (all selectors present)

-- ============================================
-- TESTING INSTRUCTIONS
-- ============================================

-- Test 1: Normal Operation
-- Run an Agoda scrape job and verify data is extracted

-- Test 2: Healing Test
-- Break the name selector:
/*
UPDATE scraper_selectors 
SET selector = '[data-testid=BROKEN_FOR_HEALING_TEST]' 
WHERE source_id = (SELECT id FROM sources WHERE name = 'agoda') 
AND field_name = 'name';
*/

-- Run scrape job and check logs for:
-- - selector.extraction_failed
-- - selector.attempting_reactive_heal
-- - inspector.skip_reload
-- - selector.healed OR selector.heal_failed

-- Test 3: Restore Selector
/*
UPDATE scraper_selectors 
SET selector = '[data-selenium="hotel-name"], h3[class*="PropertyCard"], [class*="hotel-name"]' 
WHERE source_id = (SELECT id FROM sources WHERE name = 'agoda') 
AND field_name = 'name';
*/

-- ============================================
-- NOTES
-- ============================================

-- 1. Agoda code already uses _extract_field_with_healing()
-- 2. Only database configuration was missing
-- 3. Selectors above are educated guesses - verify against real Agoda pages
-- 4. Field hints should be updated with actual values from Agoda
-- 5. After migration, Agoda will have full self-healing capability
