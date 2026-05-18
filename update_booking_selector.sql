-- Update name selector to use data-testid
UPDATE scraper_selectors 
SET selector = '[data-testid="title"]' 
WHERE source_id = 1 AND field_name = 'name';

-- Update field hints for self-healing
UPDATE sources 
SET field_hints = jsonb_set(
    COALESCE(field_hints, '{}'::jsonb), 
    '{name}', 
    '"Atithi Hotel"'
) 
WHERE name = 'booking_com';

-- Verify updates
SELECT field_name, selector FROM scraper_selectors WHERE source_id = 1 AND field_name = 'name';
SELECT name, field_hints->'name' as name_hint FROM sources WHERE name = 'booking_com';
