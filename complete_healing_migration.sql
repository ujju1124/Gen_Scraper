-- Complete Healing Migration SQL Script
-- Adds selectors and field hints for all Playwright-based scrapers
-- Date: 2026-05-12

-- ============================================================
-- 1. OYO ROOMS (source_id = 3)
-- ============================================================

-- Add selectors
INSERT INTO scraper_selectors (source_id, field_name, selector, selector_type, is_active, verified_at)
VALUES
    (3, 'name', 'h3, [data-testid="hotel-name"], .hotelName, [class*="hotelName"]', 'css', true, NOW()),
    (3, 'address', '[title], .address, [class*="address"]', 'css', true, NOW()),
    (3, 'price', '[data-testid="price"], [class*="price"], [class*="Price"]', 'css', true, NOW()),
    (3, 'rating', '[class*="rating"], [class*="Rating"]', 'css', true, NOW())
ON CONFLICT (source_id, field_name) DO UPDATE
SET selector = EXCLUDED.selector,
    selector_type = EXCLUDED.selector_type,
    is_active = EXCLUDED.is_active,
    verified_at = EXCLUDED.verified_at;

-- Add field hints
UPDATE sources
SET field_hints = '{
    "name": "OYO Hotel Kathmandu",
    "address": "Thamel, Kathmandu",
    "price": "NPR 2500",
    "rating": "4.2"
}'::jsonb,
    heal_mode = 'AUTO'
WHERE id = 3;

-- ============================================================
-- 2. ESEWA HOTELS (source_id = 4)
-- ============================================================

-- Add selectors
INSERT INTO scraper_selectors (source_id, field_name, selector, selector_type, is_active, verified_at)
VALUES
    (4, 'name', 'h5, h4, h3, .hotel-name, .title, [class*="hotelName"]', 'css', true, NOW()),
    (4, 'price', '.price, .hotel-price, span:has-text("NPR"), [class*="price"]', 'css', true, NOW()),
    (4, 'rating', '.rating, [class*="rating"], [class*="Rating"]', 'css', true, NOW())
ON CONFLICT (source_id, field_name) DO UPDATE
SET selector = EXCLUDED.selector,
    selector_type = EXCLUDED.selector_type,
    is_active = EXCLUDED.is_active,
    verified_at = EXCLUDED.verified_at;

-- Add field hints
UPDATE sources
SET field_hints = '{
    "name": "Hotel Shanker Kathmandu",
    "price": "NPR 3500",
    "rating": "4.5"
}'::jsonb,
    heal_mode = 'AUTO'
WHERE id = 4;

-- ============================================================
-- 3. NEPALYP (source_id = 5 and all NepalYP variants)
-- ============================================================

-- Add selectors for base NepalYP (applies to all 22 NepalYP sources)
INSERT INTO scraper_selectors (source_id, field_name, selector, selector_type, is_active, verified_at)
VALUES
    (5, 'name', 'h3, h4, .company-name, .title, [class*="name"]', 'css', true, NOW()),
    (5, 'address', '.address, .location, [class*="address"], [class*="location"]', 'css', true, NOW()),
    (5, 'phone', 'a[href^="tel:"], .phone, [class*="phone"]', 'css', true, NOW()),
    (5, 'email', 'a[href^="mailto:"], .email, [class*="email"]', 'css', true, NOW())
ON CONFLICT (source_id, field_name) DO UPDATE
SET selector = EXCLUDED.selector,
    selector_type = EXCLUDED.selector_type,
    is_active = EXCLUDED.is_active,
    verified_at = EXCLUDED.verified_at;

-- Add field hints for base NepalYP
UPDATE sources
SET field_hints = '{
    "name": "Hotel Yak & Yeti",
    "address": "Durbar Marg, Kathmandu",
    "phone": "+977-1-4248999",
    "email": "info@yakandyeti.com"
}'::jsonb,
    heal_mode = 'AUTO'
WHERE id = 5;

-- Copy selectors to all other NepalYP sources (9-31)
DO $$
DECLARE
    nepalyp_source_id INT;
BEGIN
    FOR nepalyp_source_id IN 
        SELECT id FROM sources WHERE name LIKE 'nepalyp_%' AND id != 5
    LOOP
        -- Insert selectors for this NepalYP variant
        INSERT INTO scraper_selectors (source_id, field_name, selector, selector_type, is_active, verified_at)
        VALUES
            (nepalyp_source_id, 'name', 'h3, h4, .company-name, .title, [class*="name"]', 'css', true, NOW()),
            (nepalyp_source_id, 'address', '.address, .location, [class*="address"], [class*="location"]', 'css', true, NOW()),
            (nepalyp_source_id, 'phone', 'a[href^="tel:"], .phone, [class*="phone"]', 'css', true, NOW()),
            (nepalyp_source_id, 'email', 'a[href^="mailto:"], .email, [class*="email"]', 'css', true, NOW())
        ON CONFLICT (source_id, field_name) DO UPDATE
        SET selector = EXCLUDED.selector,
            selector_type = EXCLUDED.selector_type,
            is_active = EXCLUDED.is_active,
            verified_at = EXCLUDED.verified_at;
        
        -- Update field hints and heal mode
        UPDATE sources
        SET field_hints = '{
            "name": "Example Business Name",
            "address": "Thamel, Kathmandu",
            "phone": "+977-1-234567",
            "email": "info@example.com"
        }'::jsonb,
            heal_mode = 'AUTO'
        WHERE id = nepalyp_source_id;
    END LOOP;
END $$;

-- ============================================================
-- 4. FOODMANDU (source_id = 8)
-- ============================================================

-- Add selectors
INSERT INTO scraper_selectors (source_id, field_name, selector, selector_type, is_active, verified_at)
VALUES
    (8, 'name', 'div.title20 a', 'css', true, NOW()),
    (8, 'address', 'div.subtitle > div:first-child span:nth-child(2)', 'css', true, NOW()),
    (8, 'cuisine', 'div.subtitle > div:nth-child(2) span:nth-child(2)', 'css', true, NOW()),
    (8, 'thumbnail', 'div.listing__photo img', 'css', true, NOW())
ON CONFLICT (source_id, field_name) DO UPDATE
SET selector = EXCLUDED.selector,
    selector_type = EXCLUDED.selector_type,
    is_active = EXCLUDED.is_active,
    verified_at = EXCLUDED.verified_at;

-- Add field hints
UPDATE sources
SET field_hints = '{
    "name": "Bhojan Griha",
    "address": "Dillibazar, Kathmandu",
    "cuisine": "Nepali | Indian | Chinese"
}'::jsonb,
    heal_mode = 'AUTO'
WHERE id = 8;

-- ============================================================
-- 5. GOOGLE MAPS (source_id = 32) - Already has selectors, just update field hints
-- ============================================================

-- Update field hints for Google Maps
UPDATE sources
SET field_hints = '{
    "name": "Hotel Shanker",
    "address": "Lazimpat, Kathmandu 44600, Nepal",
    "phone": "+977-1-4410151",
    "rating": "4.5",
    "review_count": "1,234",
    "category_label": "Hotel",
    "business_status": "Open"
}'::jsonb,
    heal_mode = 'AUTO'
WHERE id = 32;

-- ============================================================
-- VERIFICATION QUERIES
-- ============================================================

-- Check all sources with selectors
SELECT 
    s.id,
    s.name,
    s.heal_mode,
    s.is_active,
    COUNT(ss.id) as selector_count,
    CASE WHEN s.field_hints IS NOT NULL THEN 'YES' ELSE 'NO' END as has_field_hints
FROM sources s
LEFT JOIN scraper_selectors ss ON s.id = ss.source_id
WHERE s.id IN (1, 2, 3, 4, 5, 8, 9, 10, 11, 12, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32)
GROUP BY s.id, s.name, s.heal_mode, s.is_active, s.field_hints
ORDER BY s.id;

-- Check selector details for each migrated source
SELECT 
    s.name as source_name,
    ss.field_name,
    ss.selector,
    ss.selector_type,
    ss.is_active
FROM sources s
JOIN scraper_selectors ss ON s.id = ss.source_id
WHERE s.id IN (3, 4, 5, 8, 32)
ORDER BY s.id, ss.field_name;

-- Summary statistics
SELECT 
    'Total Playwright Sources' as metric,
    COUNT(*) as count
FROM sources
WHERE id IN (1, 2, 3, 4, 5, 6, 8, 32)
UNION ALL
SELECT 
    'Sources with AUTO heal mode' as metric,
    COUNT(*) as count
FROM sources
WHERE id IN (1, 2, 3, 4, 5, 6, 8, 32) AND heal_mode = 'AUTO'
UNION ALL
SELECT 
    'Sources with selectors' as metric,
    COUNT(DISTINCT source_id) as count
FROM scraper_selectors
WHERE source_id IN (1, 2, 3, 4, 5, 6, 8, 32)
UNION ALL
SELECT 
    'Sources with field hints' as metric,
    COUNT(*) as count
FROM sources
WHERE id IN (1, 2, 3, 4, 5, 6, 8, 32) AND field_hints IS NOT NULL;

