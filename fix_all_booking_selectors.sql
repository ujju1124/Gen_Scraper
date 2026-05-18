-- Fix ALL corrupted Booking.com selectors
-- These were corrupted during a previous update attempt

-- Fix rating_overall
UPDATE scraper_selectors 
SET selector = 'div[data-testid="review-score-component"] div'
WHERE source_id = 1 AND field_name = 'rating_overall';

-- Fix review_count  
UPDATE scraper_selectors
SET selector = '[data-testid="review-score"]'
WHERE source_id = 1 AND field_name = 'review_count';

-- Fix star_rating
UPDATE scraper_selectors
SET selector = '[data-testid="rating-stars"]'
WHERE source_id = 1 AND field_name = 'star_rating';

-- Fix thumbnail_url
UPDATE scraper_selectors
SET selector = '[data-testid="image"]'
WHERE source_id = 1 AND field_name = 'thumbnail_url';

-- Fix property_type
UPDATE scraper_selectors
SET selector = '[data-testid="property-type"]'
WHERE source_id = 1 AND field_name = 'property_type';

-- Fix amenities
UPDATE scraper_selectors
SET selector = '[data-testid="facility"]'
WHERE source_id = 1 AND field_name = 'amenities';

-- Fix description_short
UPDATE scraper_selectors
SET selector = '[data-testid="property-description"]'
WHERE source_id = 1 AND field_name = 'description_short';

-- Fix detail selectors
UPDATE scraper_selectors
SET selector = '[data-testid="rating-stars"]'
WHERE source_id = 1 AND field_name = 'detail_star_rating';

UPDATE scraper_selectors
SET selector = 'P.review_score_value'
WHERE source_id = 1 AND field_name = 'detail_review_score';

UPDATE scraper_selectors
SET selector = 'DIV.b99b6ef58f:first-of-type'
WHERE source_id = 1 AND field_name = 'detail_checkin';

UPDATE scraper_selectors
SET selector = 'DIV.b99b6ef58f:last-of-type'
WHERE source_id = 1 AND field_name = 'detail_checkout';

UPDATE scraper_selectors
SET selector = 'P.b99b6ef58f.f1152bae71'
WHERE source_id = 1 AND field_name = 'detail_description';

UPDATE scraper_selectors
SET selector = 'SPAN.f6b6d2a959'
WHERE source_id = 1 AND field_name = 'detail_languages';

UPDATE scraper_selectors
SET selector = 'script[type="application/ld+json"]'
WHERE source_id = 1 AND field_name = 'detail_jsonld';

UPDATE scraper_selectors
SET selector = '[data-testid="property-most-popular-facilities-wrapper"] span'
WHERE source_id = 1 AND field_name = 'detail_amenities';

UPDATE scraper_selectors
SET selector = '[data-testid="review-subscore"]'
WHERE source_id = 1 AND field_name = 'detail_review_category';

-- Verify the fixes
SELECT field_name, selector, is_active 
FROM scraper_selectors 
WHERE source_id = 1 
ORDER BY field_name;
