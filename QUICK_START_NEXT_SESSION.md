# Quick Start - Next Session

**Last Session**: 2026-05-12  
**Status**: Skip-Reload Fix Verified ✅  
**Next**: Complete Agoda Migration

---

## What Happened Last Session

✅ **MAJOR WIN**: Skip-reload fix verified working!
- No more 30-second timeouts
- Healing completes in 75ms
- System is production-ready

✅ **Discovery**: Agoda code already uses healing system!
- Only needs database configuration
- SQL script ready to run

---

## Start Here

### Step 1: Restart Docker (if needed)

```bash
# Check if Docker is running
docker-compose ps

# If not running, start it
docker-compose up -d
```

### Step 2: Complete Agoda Migration

```bash
# Run the migration script
docker-compose exec -T postgres psql -U scraper -d scraper_db < complete_agoda_migration.sql

# Verify configuration
docker-compose exec -T postgres psql -U scraper -d scraper_db -c "
SELECT s.name, s.heal_mode, ss.field_name, ss.selector 
FROM sources s 
LEFT JOIN scraper_selectors ss ON s.id = ss.source_id 
WHERE s.name = 'agoda' 
ORDER BY ss.field_name;
"
```

### Step 3: Test Agoda Healing

```bash
# 1. Break the name selector
docker-compose exec -T postgres psql -U scraper -d scraper_db -c "
UPDATE scraper_selectors 
SET selector = '[data-testid=BROKEN_FOR_HEALING_TEST]' 
WHERE source_id = (SELECT id FROM sources WHERE name = 'agoda') 
AND field_name = 'name';
"

# 2. Create test job
docker-compose exec -T postgres psql -U scraper -d scraper_db -c "
INSERT INTO scrape_jobs (id, user_id, category_id, location, source_ids, max_results, status, created_at) 
VALUES (gen_random_uuid(), 1, 1, 'Kathmandu', ARRAY[(SELECT id FROM sources WHERE name = 'agoda')], 3, 'PENDING', NOW()) 
RETURNING id;
"
# Note the returned job ID

# 3. Trigger the job
docker-compose exec -T backend python -c "
from celery import Celery
import os

redis_url = os.getenv('REDIS_URL', 'redis://redis:6379/0')
celery_app = Celery('tasks', broker=redis_url, backend=redis_url)

result = celery_app.send_task('tasks.scrape_task', args=['YOUR_JOB_ID_HERE'])
print(f'Job triggered: {result.id}')
"

# 4. Monitor logs for healing events
docker-compose logs -f worker | grep -E "selector\.|inspector\."

# Look for:
# - selector.extraction_failed
# - selector.attempting_reactive_heal
# - inspector.skip_reload ← THE KEY EVENT!
# - selector.healed OR selector.heal_failed

# 5. Restore selector
docker-compose exec -T postgres psql -U scraper -d scraper_db -c "
UPDATE scraper_selectors 
SET selector = '[data-selenium=\"hotel-name\"], h3[class*=\"PropertyCard\"]' 
WHERE source_id = (SELECT id FROM sources WHERE name = 'agoda') 
AND field_name = 'name';
"
```

---

## If Agoda Test Passes

### Move to Hostelworld Migration

**Estimated Time**: 2 hours

**Steps**:

1. **Read current implementation**:
   ```bash
   # Check if Hostelworld exists
   docker-compose exec -T postgres psql -U scraper -d scraper_db -c "
   SELECT id, name, base_url FROM sources WHERE name LIKE '%hostel%';
   "
   ```

2. **Examine code**:
   - Open `backend/scrapers/hostelworld.py`
   - Find `_extract_hotels_from_page()` method
   - Identify extraction points

3. **Modify code**:
   - Replace hardcoded selectors with `_extract_field_with_healing()`
   - Update method signature to include `page, source, db`
   - Update all call sites

4. **Add to database**:
   - Create SQL script similar to `complete_agoda_migration.sql`
   - Add selectors (inspect Hostelworld website for actual selectors)
   - Add field hints (real values from website)
   - Set heal_mode to AUTO

5. **Test**:
   - Normal operation test
   - Healing test (break selector)
   - Verify skip-reload works
   - Restore selector

6. **Document**:
   - Update `HEALING_SYSTEM_STATUS_AND_NEXT_STEPS.md`
   - Mark Hostelworld as complete

---

## Key Documents

### For Implementation
- `SCRAPER_HEALING_MIGRATION_GUIDE.md` - Step-by-step guide
- `complete_agoda_migration.sql` - Example SQL script

### For Testing
- `HEALING_VERIFICATION_CHECKLIST.md` - Verification commands
- `WHEN_TEST_COMPLETES_RUN_THIS.md` - Quick reference

### For Status
- `HEALING_SYSTEM_STATUS_AND_NEXT_STEPS.md` - Current status
- `SESSION_SUMMARY.md` - What we accomplished

### For Understanding
- `SKIP_RELOAD_FIX_VERIFIED.md` - Test results
- `REACTIVE_HEALING_SKIP_RELOAD_FIX.md` - Technical details

---

## Success Checklist

### Agoda Migration
- [ ] SQL script run successfully
- [ ] Selectors verified in database
- [ ] Field hints configured
- [ ] Heal mode set to AUTO
- [ ] Normal scrape works
- [ ] Healing test passes
- [ ] Skip-reload verified
- [ ] Selector restored

### Hostelworld Migration
- [ ] Code modified to use healing
- [ ] Selectors added to database
- [ ] Field hints configured
- [ ] Heal mode set to AUTO
- [ ] Normal scrape works
- [ ] Healing test passes
- [ ] Skip-reload verified
- [ ] Documentation updated

---

## Common Issues & Solutions

### Issue: Docker not starting
**Solution**: Restart Docker Desktop application

### Issue: Selectors not found
**Solution**: Inspect actual website HTML to find correct selectors

### Issue: Field hints too generic
**Solution**: Use specific real values from the website

### Issue: Healing confidence too low
**Solution**: 
- Check if field hint appears on page
- Make field hint more specific
- Verify selector type priority (testid > ARIA > XPath > CSS)

### Issue: Timeout still occurring
**Solution**: 
- Verify skip-reload fix is in code
- Check domain extraction logic
- Ensure page URL matches source base_url

---

## Quick Commands

### Check Job Status
```bash
docker-compose exec -T postgres psql -U scraper -d scraper_db -c "
SELECT id, status, error_message FROM scrape_jobs 
WHERE id = 'YOUR_JOB_ID' 
ORDER BY created_at DESC LIMIT 1;
"
```

### Check Healing Log
```bash
docker-compose exec -T postgres psql -U scraper -d scraper_db -c "
SELECT field_name, old_selector, new_selector, confidence, status 
FROM selector_heal_log 
WHERE source_id = YOUR_SOURCE_ID 
ORDER BY healed_at DESC LIMIT 5;
"
```

### Check Selectors
```bash
docker-compose exec -T postgres psql -U scraper -d scraper_db -c "
SELECT field_name, selector, selector_type, is_active 
FROM scraper_selectors 
WHERE source_id = YOUR_SOURCE_ID 
ORDER BY field_name;
"
```

### View Recent Logs
```bash
docker-compose logs --tail=100 worker | grep -E "selector\.|inspector\."
```

---

## Timeline

### Today (2-3 hours)
- Complete Agoda migration (1 hour)
- Test Agoda healing (30 min)
- Start Hostelworld migration (1-2 hours)

### This Week (10-15 hours)
- Complete Hostelworld (2 hours)
- Complete OYO Rooms (2 hours)
- Complete eSewa Hotels (2 hours)
- Test all migrations (2 hours)
- Start NepalYP (4 hours)

### Next Week (15-20 hours)
- Complete NepalYP (4 hours)
- Complete DirectoryOfNepal (3 hours)
- Complete Foodmandu (3 hours)
- Complete Google Maps (6 hours)
- Build admin panel (10 hours)

---

## Remember

1. **Skip-reload fix is verified** - No more timeouts!
2. **Agoda code is ready** - Only needs DB config
3. **Follow the migration guide** - It has all the steps
4. **Test each scraper** - Don't skip the healing test
5. **Document progress** - Update status document

---

## Questions to Answer

1. Do Agoda selectors work with real website?
2. Does skip-reload work for Agoda?
3. What's the healing success rate?
4. Are field hints specific enough?
5. Does the system handle edge cases?

---

**Ready to Start**: Run Step 1 above!

**Estimated Session Time**: 2-3 hours for Agoda + Hostelworld

**Goal**: 2 more scrapers fully migrated with healing
