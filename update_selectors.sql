-- Update selectors with working ones from browser testing

-- Update amenities selector (VERIFIED WORKING)
UPDATE scraper_selectors 
SET selector = '[data-testid="property-most-popular-facilities-wrapper"] span',
    is_active = true
WHERE source_id = 1 AND field_name = 'detail_amenities';

-- Add new selector for house rules section (contains check-in/checkout)
INSERT INTO scraper_selectors (source_id, field_name, selector, selector_type, is_active)
VALUES (1, 'detail_house_rules', '[data-testid="property-section--content"]', 'css', true)
ON CONFLICT (source_id, field_name) 
DO UPDATE SET 
  selector = EXCLUDED.selector,
  is_active = true;

-- Deactivate old broken selectors
UPDATE scraper_selectors 
SET is_active = false
WHERE source_id = 1 
  AND field_name IN ('detail_checkin', 'detail_checkout', 'detail_description', 'detail_languages', 'detail_rating');
