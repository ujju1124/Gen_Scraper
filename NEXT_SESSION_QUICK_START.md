# Next Session Quick Start

**Last Updated**: 2026-05-12  
**Current Status**: 2/9 scrapers migrated (Booking.com verified, Agoda blocked)  
**Next Action**: Migrate OYO Rooms, eSewa Hotels, or NepalYP

---

## Quick Status

### ✅ Complete
- Booking.com: Fully migrated and tested
- Agoda: Fully migrated but blocked by anti-bot
- Skip-reload fix: Verified working

### ⏳ Next
- Find accessible scraper to migrate
- Test healing system on new scraper
- Build momentum with quick wins

---

## Start Here

### Step 1: Check Docker

```bash
docker-compose ps
```

If not running:
```bash
docker-compose up -d
```

### Step 2: Choose Next Scraper

Try in this order until one is accessible:

1. **OYO Rooms**
2. **eSewa Hotels**
3. **NepalYP**

### Step 3: Inspect Scraper

```bash
# Read the scraper code
# Check if it uses Playwright or httpx
# Check if it uses selectors or text parsing
```

### Step 4: Test Accessibility

Create a test job to see if the scraper can access the website:

```bash
# Get source ID
docker-compose exec -T postgres psql -U scraper -d scraper_db -c "
SELECT id, name, is_active FROM sources WHERE name = 'SOURCE_NAME';
"

# Create test job
docker-compose exec -T postgres psql -U scraper -d scraper_db -c "
INSERT INTO scrape_jobs (id, user_id, category_id, location, source_ids, max_results, status, created_at) 
VALUES (gen_random_uuid(), 1, 1, 'Kathmandu', ARRAY[SOURCE_ID], 3, 'PENDING', NOW()) 
RETURNING id;
"

# Trigger job
docker-compose exec backend python -c "
from celery import Celery
import os
redis_url = os.getenv('REDIS_URL', 'redis://redis:6379/0')
celery_app = Celery('tasks', broker=redis_url, backend=redis_url)
result = celery_app.send_task('tasks.scrape_task', args=['JOB_ID'])
print(f'Job triggered: {result.id}')
"

# Monitor logs
docker-compose logs -f worker | grep -E "SOURCE_NAME|selector|inspector"
```

### Step 5: If Accessible, Migrate

Follow the migration guide:
1. Inspect website for selectors
2. Add selectors to database
3. Modify scraper code
4. Test healing

### Step 6: If Blocked, Try Next

Move to the next scraper in the list.

---

## Migration Checklist

### Database Setup

```sql
-- Add selectors
INSERT INTO scraper_selectors (source_id, field_name, selector, selector_type, is_active)
VALUES
    (SOURCE_ID, 'name', 'ACTUAL_SELECTOR', 'css', true),
    (SOURCE_ID, 'address', 'ACTUAL_SELECTOR', 'css', true),
    (SOURCE_ID, 'price', 'ACTUAL_SELECTOR', 'css', true),
    (SOURCE_ID, 'rating', 'ACTUAL_SELECTOR', 'css', true);

-- Add field hints
UPDATE sources
SET field_hints = '{
    "name": "Real Hotel Name",
    "address": "Real Address",
    "price": "NPR 5000",
    "rating": "8.5"
}'::jsonb
WHERE id = SOURCE_ID;

-- Set heal mode
UPDATE sources SET heal_mode = 'AUTO' WHERE id = SOURCE_ID;
```

### Code Changes

```python
# Replace hardcoded extraction with healing
name = await self._extract_field_with_healing(
    card=card,
    page=page,
    source=source,
    db=db,
    field_name='name'
)
```

### Testing

```bash
# 1. Break selector
docker-compose exec -T postgres psql -U scraper -d scraper_db -c "
UPDATE scraper_selectors 
SET selector = '[data-testid=BROKEN_FOR_TEST]' 
WHERE source_id = SOURCE_ID AND field_name = 'name';
"

# 2. Create test job
# 3. Monitor logs for healing events
# 4. Restore selector
```

---

## Key Documents

### For Understanding
- `SKIP_RELOAD_FIX_VERIFIED.md` - Booking.com test results
- `AGODA_HEALING_TEST_RESULTS.md` - Agoda test results
- `SESSION_PROGRESS_SUMMARY.md` - Current status

### For Implementation
- `SCRAPER_HEALING_MIGRATION_GUIDE.md` - Step-by-step guide
- `backend/scrapers/booking_com.py` - Reference implementation
- `backend/scrapers/agoda.py` - Another example

### For Planning
- `HEALING_SYSTEM_STATUS_AND_NEXT_STEPS.md` - Overall roadmap
- `HOSTELWORLD_MIGRATION_PLAN.md` - Complex migration example

---

## Common Commands

### Check Source Status
```bash
docker-compose exec -T postgres psql -U scraper -d scraper_db -c "
SELECT id, name, is_active, heal_mode, 
       (SELECT COUNT(*) FROM scraper_selectors WHERE source_id = sources.id) as selector_count
FROM sources 
WHERE category_id = 1 
ORDER BY name;
"
```

### Check Job Status
```bash
docker-compose exec -T postgres psql -U scraper -d scraper_db -c "
SELECT id, status, source_ids, location, created_at 
FROM scrape_jobs 
WHERE status IN ('PENDING', 'RUNNING') 
ORDER BY created_at DESC 
LIMIT 5;
"
```

### Check Healing Log
```bash
docker-compose exec -T postgres psql -U scraper -d scraper_db -c "
SELECT source_id, field_name, confidence, status, healed_at 
FROM selector_heal_log 
ORDER BY healed_at DESC 
LIMIT 10;
"
```

### View Recent Logs
```bash
docker-compose logs --tail=50 worker | grep -E "selector|inspector"
```

---

## Decision Tree

```
Start
  ↓
Read scraper code
  ↓
Uses Playwright? ──No──→ Skip (not applicable)
  ↓ Yes
  ↓
Test accessibility
  ↓
Accessible? ──No──→ Mark as blocked, try next
  ↓ Yes
  ↓
Uses selectors? ──No──→ Complex migration (3-4 hours)
  ↓ Yes
  ↓
Migrate (1-2 hours)
  ↓
Test healing
  ↓
Success? ──No──→ Debug and fix
  ↓ Yes
  ↓
Document and move to next
```

---

## Success Criteria

### Per Scraper
- [ ] Code uses `_extract_field_with_healing()`
- [ ] Selectors in database
- [ ] Field hints configured
- [ ] Heal mode set to AUTO
- [ ] Normal scrape works
- [ ] Healing test passes
- [ ] Skip-reload verified
- [ ] Documentation updated

### Overall
- [ ] 4/9 scrapers verified (target for this week)
- [ ] Patterns documented
- [ ] Admin panel planned
- [ ] Production timeline defined

---

## Tips

1. **Start with accessibility test** - Don't waste time migrating if blocked
2. **Use Booking.com as reference** - It's the gold standard
3. **Document as you go** - Helps with next scraper
4. **Don't get stuck** - If blocked or complex, move to next
5. **Build momentum** - Quick wins motivate progress

---

## Expected Outcomes

### Best Case
- 3 scrapers migrated today
- All accessible and simple
- Healing verified on all
- Clear path to completion

### Realistic Case
- 1-2 scrapers migrated today
- Some blocked by anti-bot
- Healing verified on accessible ones
- Need to adjust strategy

### Worst Case
- All scrapers blocked
- Need anti-bot solutions
- Focus on admin panel instead
- Revisit with proxies

---

**Ready to start!**

**First action**: Read OYO Rooms scraper code

**Estimated session time**: 2-3 hours

**Goal**: Migrate at least 1 scraper successfully

