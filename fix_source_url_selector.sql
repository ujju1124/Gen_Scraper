-- Fix corrupted source_url selector for Booking.com
UPDATE scraper_selectors 
SET selector = '[data-testid="title-link"]'
WHERE source_id = 1 AND field_name = 'source_url';

-- Verify the update
SELECT field_name, selector, is_active 
FROM scraper_selectors 
WHERE source_id = 1 AND field_name = 'source_url';
