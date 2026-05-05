# Priority 4 - Hostelworld Implementation Plan

**Status:** Ready to implement  
**Estimated Time:** 2 hours

---

## Implementation Steps

### Step 1: Add Selectors to Database (15 min)

Create SQL to insert Hostelworld selectors:

```sql
-- Get hostelworld source_id
SELECT id FROM sources WHERE name = 'hostelworld';

-- Insert selectors (assuming source_id = 5, adjust based on query result)
INSERT INTO scraper_selectors (source_id, field_name, selector, is_active) VALUES
  ((SELECT id FROM sources WHERE name='hostelworld'), 'card_container', 'a[href*="/hostels/p/"]', TRUE),
  ((SELECT id FROM sources WHERE name='hostelworld'), 'name', 'h3, h2', TRUE),
  ((SELECT id FROM sources WHERE name='hostelworld'), 'rating_text', 'span', TRUE),
  ((SELECT id FROM sources WHERE name='hostelworld'), 'distance', 'span', TRUE),
  ((SELECT id FROM sources WHERE name='hostelworld'), 'price_text', 'span', TRUE),
  ((SELECT id FROM sources WHERE name='hostelworld'), 'description', 'p', TRUE),
  ((SELECT id FROM sources WHERE name='hostelworld'), 'detail_link', 'self', TRUE),
  ((SELECT id FROM sources WHERE name='hostelworld'), 'thumbnail', 'img', TRUE),
  ((SELECT id FROM sources WHERE name='hostelworld'), 'pagination_next', 'a[href*="?page="]', TRUE)
ON CONFLICT (source_id, field_name) DO UPDATE SET
  selector = EXCLUDED.selector,
  is_active = EXCLUDED.is_active;
```

### Step 2: Implement Scraping Logic (45 min)

Update `backend/scrapers/hostelworld.py`:
- Remove HUMAN CHECKPOINT block
- Implement full scraping logic
- Handle pagination
- Extract all fields
- Parse prices and ratings

### Step 3: Update seed.py (5 min)

Change Hostelworld from inactive to active:
```python
("hostelworld", "Hostelworld", "https://www.hostelworld.com", True),  # ACTIVE
```

### Step 4: Run Seed Script (5 min)

```bash
docker exec gen_scraper-backend-1 python seed.py
```

### Step 5: Test with Live Job (30 min)

Create test job via Playwright:
- Category: Hotels
- Location: Kathmandu
- Max results: 25
- Verify 10+ results returned

### Step 6: Adjust Selectors if Needed (20 min)

If test fails:
- Check logs for errors
- Adjust selectors in database
- Re-run test

---

## Let's Start!

I'll begin with Step 1 - adding selectors to the database.
