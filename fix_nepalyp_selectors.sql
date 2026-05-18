-- Fix NepalYP selectors with correct patterns

-- Update name selector for all NepalYP sources
UPDATE scraper_selectors 
SET selector = 'h2 a, h3 a, .company-name a, [class*="name"] a, a[href*="/company/"]'
WHERE source_id IN (SELECT id FROM sources WHERE name LIKE 'nepalyp%') 
AND field_name = 'name';

-- Update phone selector for all NepalYP sources
UPDATE scraper_selectors 
SET selector = 'a[href^="tel:"], [class*="phone"], [class*="contact"], [itemprop="telephone"]'
WHERE source_id IN (SELECT id FROM sources WHERE name LIKE 'nepalyp%') 
AND field_name = 'phone';

-- Update address selector for all NepalYP sources
UPDATE scraper_selectors 
SET selector = '[itemprop="address"], .address, [class*="addr"], [class*="location"]'
WHERE source_id IN (SELECT id FROM sources WHERE name LIKE 'nepalyp%') 
AND field_name = 'address';

-- Update email selector for all NepalYP sources
UPDATE scraper_selectors 
SET selector = 'a[href^="mailto:"], [itemprop="email"], [class*="email"]'
WHERE source_id IN (SELECT id FROM sources WHERE name LIKE 'nepalyp%') 
AND field_name = 'email';

-- Verify updates
SELECT s.name, ss.field_name, ss.selector 
FROM scraper_selectors ss 
JOIN sources s ON ss.source_id = s.id 
WHERE s.name LIKE 'nepalyp%' 
ORDER BY s.name, ss.field_name 
LIMIT 20;
