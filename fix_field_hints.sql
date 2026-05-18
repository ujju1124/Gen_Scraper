-- Fix Google Maps field_hints for better healing
UPDATE sources 
SET field_hints = jsonb_set(
  field_hints, 
  '{review_count}', 
  '"(1,234)"'::jsonb
) 
WHERE name = 'google_maps';

-- Verify the update
SELECT name, field_hints->'review_count' as review_count_hint 
FROM sources 
WHERE name = 'google_maps';
