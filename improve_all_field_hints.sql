-- Improve all Google Maps field_hints for better healing confidence

UPDATE sources 
SET field_hints = jsonb_build_object(
  'name', 'Hotel Shanker',
  'phone', '+977-1-4410151',
  'rating', '4.5',
  'address', 'Lazimpat, Kathmandu 44600, Nepal',
  'review_count', '(1,234)',
  'category_label', 'Hotel',
  'business_status', 'OPEN',
  'price_range', '$$',
  'website', 'hotelshanker.com'
)
WHERE name = 'google_maps';

-- Verify
SELECT name, field_hints 
FROM sources 
WHERE name = 'google_maps';
