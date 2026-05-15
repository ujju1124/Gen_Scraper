INSERT INTO scraper_selectors (source_id, field_name, selector, selector_type, is_active)
VALUES
  (1, 'detail_checkin', 'DIV.b99b6ef58f', 'css', true),
  (1, 'detail_checkout', 'DIV.b99b6ef58f', 'css', true),
  (1, 'detail_description', 'P.b99b6ef58f.f1152bae71', 'css', true),
  (1, 'detail_languages', 'SPAN.f6b6d2a959', 'css', true),
  (1, 'detail_amenities', 'span[data-testid="facility-name"], .e50d7535fa', 'css', true),
  (1, 'detail_rating', 'div.a9918d47bf', 'css', true)
ON CONFLICT (source_id, field_name) 
DO UPDATE SET 
  selector = EXCLUDED.selector,
  is_active = true;
