# City Expansion - In Progress 🚀

**Date**: May 13, 2026  
**Status**: 🔄 IN PROGRESS  
**Jobs Created**: 12  
**Expected Duration**: 2-3 hours

---

## Jobs Created

All 12 jobs created successfully:

| Category | Source | City | Max Results | Status |
|----------|--------|------|-------------|--------|
| hotels | nepalyp | Biratnagar | 100 | ✅ Created |
| hotels | nepalyp | Birgunj | 100 | ✅ Created |
| hotels | nepalyp | Butwal | 100 | ✅ Created |
| hotels | nepalyp | Hetauda | 100 | ✅ Created |
| restaurants | nepalyp_restaurants | Biratnagar | 100 | ✅ Created |
| restaurants | nepalyp_restaurants | Birgunj | 100 | ✅ Created |
| restaurants | nepalyp_restaurants | Butwal | 100 | ✅ Created |
| hospitals | nepalyp_hospitals | Pokhara | 100 | ✅ Created |
| hospitals | nepalyp_hospitals | Biratnagar | 100 | ✅ Created |
| pharmacies | nepalyp_pharmacies | Pokhara | 100 | ✅ Created |
| banks | nepalyp_banks | Pokhara | 100 | ✅ Created |
| banks | nepalyp_banks | Biratnagar | 100 | ✅ Created |

**Total**: 12 jobs × 100 results = **1,200 expected new results**

---

## Initial Status (Start Time)

**Job Queue**:
```
 status  | count 
---------+-------
 DONE    |    72
 QUEUED  |    11
 RUNNING |     2
```

**Total Results**: 5,132

**City Distribution** (Top 10):
```
   city    | count 
-----------+-------
 Kathmandu |  3101
 Chitwan   |   485
 Pokhara   |   313
 Sunsari   |   242
 Rupandehi |   165
 Lalitpur  |   109
 Morang    |    85
 Tanahu    |    70
 Sarlahi   |    70
 Lamjung   |    70
```

---

## Target Cities

### Primary Expansion Cities
1. **Biratnagar** - 5 jobs (hotels, restaurants, hospitals, banks)
2. **Birgunj** - 2 jobs (hotels, restaurants)
3. **Butwal** - 2 jobs (hotels, restaurants)
4. **Hetauda** - 1 job (hotels)

### Secondary Expansion (Pokhara)
- 3 jobs (hospitals, pharmacies, banks)
- Pokhara already has 313 results, expanding to other categories

---

## Monitoring Commands

### Check Job Status
```bash
docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c \
  "SELECT status, COUNT(*) FROM scrape_jobs WHERE status != 'CANCELLED' GROUP BY status;"
```

### Check Total Results
```bash
docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c \
  "SELECT COUNT(*) as total FROM cleaned_results;"
```

### Check City Distribution
```bash
docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c \
  "SELECT city, COUNT(*) FROM cleaned_results GROUP BY city ORDER BY COUNT(*) DESC LIMIT 10;"
```

### Check New Cities Added
```bash
docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c \
  "SELECT city, COUNT(*) FROM cleaned_results \
   WHERE city IN ('Biratnagar', 'Birgunj', 'Butwal', 'Hetauda') \
   GROUP BY city ORDER BY COUNT(*) DESC;"
```

### Check Worker Logs
```bash
docker-compose logs --tail=50 worker --since 5m
```

---

## Expected Outcomes

### Goal
- **Target**: 7,000+ total records
- **Current**: 5,132 records
- **Expected New**: ~1,200 records
- **Final Total**: ~6,300 records

### City Coverage
- **Before**: Heavily concentrated in Kathmandu (60%)
- **After**: More balanced distribution across 4+ major cities

### Categories
- Hotels: 4 new cities
- Restaurants: 3 new cities
- Hospitals: 2 cities (including Pokhara expansion)
- Pharmacies: 1 city (Pokhara)
- Banks: 2 cities

---

## Performance Characteristics

### Why This Batch is Fast
1. **NepalYP Only** - No Google Maps (no browser automation)
2. **httpx-based** - Fast HTTP requests, no Playwright overhead
3. **No Anti-Bot Delays** - NepalYP doesn't require browser fingerprinting
4. **Parallel Processing** - Worker can process multiple jobs simultaneously

### Expected Timeline
- **Start**: May 13, 2026 (current time)
- **Duration**: 2-3 hours
- **Completion**: ~2-3 hours from now

### Resource Usage
- **Memory**: Low (httpx uses minimal memory vs Playwright)
- **CPU**: Moderate (JSON parsing, database writes)
- **Network**: Moderate (HTTP requests to NepalYP)

---

## Self-Healing System

The self-healing selector system is active and monitoring all scrapes:

- **Heal Mode**: AUTO for all NepalYP sources
- **Confidence Threshold**: 0.7
- **Skip-Reload Optimization**: Active
- **Heal Logs**: Being created for any selector failures

### Current Heal Status
```bash
docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c \
  "SELECT source_id, field_name, status, COUNT(*) \
   FROM selector_heal_log \
   GROUP BY source_id, field_name, status \
   ORDER BY source_id, field_name;"
```

---

## Progress Checkpoints

### Checkpoint 1: 30 Minutes
- [ ] Check job status (expect 4-6 DONE)
- [ ] Check total results (expect ~5,500)
- [ ] Check for any FAILED jobs
- [ ] Check heal logs for new entries

### Checkpoint 2: 1 Hour
- [ ] Check job status (expect 8-10 DONE)
- [ ] Check total results (expect ~5,800)
- [ ] Check city distribution (new cities appearing)

### Checkpoint 3: 2 Hours
- [ ] Check job status (expect all DONE)
- [ ] Check total results (expect ~6,300)
- [ ] Verify all target cities have data

### Final Verification
- [ ] All 12 jobs DONE
- [ ] Total results ≥ 6,000
- [ ] All 4 target cities have data
- [ ] No FAILED jobs
- [ ] Heal logs reviewed

---

## Troubleshooting

### If Jobs Stuck in QUEUED
```bash
# Check worker status
docker-compose ps worker

# Restart worker if needed
docker-compose restart worker
```

### If Jobs FAILED
```bash
# Check error messages
docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c \
  "SELECT id, location, error_message FROM scrape_jobs WHERE status = 'FAILED' ORDER BY created_at DESC LIMIT 5;"

# Check worker logs
docker-compose logs --tail=100 worker | grep -i error
```

### If Memory Issues
```bash
# Check Docker memory usage
docker stats --no-stream

# Increase memory if needed (see INCREASE_DOCKER_MEMORY.md)
```

---

## Next Steps After Completion

1. **Verify Results**
   - Check total count ≥ 6,000
   - Verify city distribution
   - Check data quality

2. **Review Heal Logs**
   - Check for any PENDING heals
   - Resolve any selector issues

3. **Update Documentation**
   - Create CITY_EXPANSION_COMPLETE.md
   - Update README.md with new coverage stats

4. **Deploy to Production** (if applicable)
   - Run final test suite
   - Create deployment checklist
   - Deploy with zero downtime

---

**Script Used**: `backend/city_expansion_jobs.py`  
**Created By**: Kiro AI  
**Monitoring**: Every 30 minutes recommended
