# NepalYP Category Scrapers Verification Test

**Date**: May 2, 2026  
**Purpose**: Verify that NepalYP category scrapers (Restaurants, Pharmacies, Hospitals) return real data

---

## Test Setup

### Sources Created and Activated ✅
```
nepalyp_restaurants → Category: Restaurants (ID: 6) → ACTIVE
nepalyp_pharmacies → Category: Pharmacies (ID: 9) → ACTIVE
nepalyp_hospitals → Category: Hospitals (ID: 10) → ACTIVE
nepalyp_drugstores → Category: Pharmacies (ID: 9) → ACTIVE
```

### Registry Verification ✅
All sources are registered in `backend/scrapers/registry.py`:
- `nepalyp_restaurants` → `NepalYPScraper`
- `nepalyp_pharmacies` → `NepalYPScraper`
- `nepalyp_hospitals` → `NepalYPScraper`
- `nepalyp_drugstores` → `NepalYPScraper`

### Scraper Logic ✅
The `NepalYPScraper` class has `_get_category_from_source_name()` method that:
- Extracts category from source name (e.g., `nepalyp_restaurants` → `Restaurants`)
- Builds dynamic URLs: `https://www.nepalyp.com/category/{Category}/city:{Location}`
- Should work for any category without code changes

---

## Test Jobs to Run

### Test 1: Restaurants
```bash
# Via API
curl -X POST http://localhost:8000/api/v1/jobs \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "category_id": 6,
    "location": "Kathmandu",
    "source_ids": [<nepalyp_restaurants_source_id>],
    "max_results": 25
  }'
```

**Expected URL**: `https://www.nepalyp.com/category/Restaurants/city:Kathmandu`  
**Expected Results**: ~1,234 restaurants in Kathmandu (will return 25)

### Test 2: Pharmacies
```bash
curl -X POST http://localhost:8000/api/v1/jobs \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "category_id": 9,
    "location": "Kathmandu",
    "source_ids": [<nepalyp_pharmacies_source_id>],
    "max_results": 25
  }'
```

**Expected URL**: `https://www.nepalyp.com/category/Pharmacies/city:Kathmandu`  
**Expected Results**: Pharmacy listings from NepalYP

### Test 3: Hospitals
```bash
curl -X POST http://localhost:8000/api/v1/jobs \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "category_id": 10,
    "location": "Kathmandu",
    "source_ids": [<nepalyp_hospitals_source_id>],
    "max_results": 25
  }'
```

**Expected URL**: `https://www.nepalyp.com/category/Hospitals/city:Kathmandu`  
**Expected Results**: ~503 hospitals in Kathmandu (will return 25)

---

## How to Run Tests

### Option 1: Via Frontend (Easiest)
1. Open http://localhost:5173
2. Login as admin
3. Go to "Create Job" page
4. Select:
   - Category: Restaurants
   - Location: Kathmandu
   - Sources: Check "NepalYP Restaurants"
   - Max Results: 25
5. Click "Start Scraping"
6. Monitor job status
7. Repeat for Pharmacies and Hospitals

### Option 2: Via API (Programmatic)
1. Get auth token:
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"admin123"}'
```

2. Get source IDs:
```bash
curl http://localhost:8000/api/v1/sources \
  -H "Authorization: Bearer YOUR_TOKEN"
```

3. Create jobs using the curl commands above

### Option 3: Via Python Script
```python
import requests

# Login
response = requests.post('http://localhost:8000/api/v1/auth/login', json={
    'email': 'admin@example.com',
    'password': 'admin123'
})
token = response.json()['access_token']

headers = {'Authorization': f'Bearer {token}'}

# Get sources
sources = requests.get('http://localhost:8000/api/v1/sources', headers=headers).json()
nepalyp_restaurants_id = [s['id'] for s in sources if s['name'] == 'nepalyp_restaurants'][0]
nepalyp_pharmacies_id = [s['id'] for s in sources if s['name'] == 'nepalyp_pharmacies'][0]
nepalyp_hospitals_id = [s['id'] for s in sources if s['name'] == 'nepalyp_hospitals'][0]

# Create test jobs
jobs = []
for category_id, source_id, name in [
    (6, nepalyp_restaurants_id, 'Restaurants'),
    (9, nepalyp_pharmacies_id, 'Pharmacies'),
    (10, nepalyp_hospitals_id, 'Hospitals')
]:
    response = requests.post('http://localhost:8000/api/v1/jobs', headers=headers, json={
        'category_id': category_id,
        'location': 'Kathmandu',
        'source_ids': [source_id],
        'max_results': 25
    })
    job = response.json()
    jobs.append((name, job['id']))
    print(f"Created {name} job: {job['id']}")

# Monitor jobs
import time
for name, job_id in jobs:
    while True:
        response = requests.get(f'http://localhost:8000/api/v1/jobs/{job_id}', headers=headers)
        job = response.json()
        print(f"{name}: {job['status']}")
        if job['status'] in ['DONE', 'FAILED']:
            break
        time.sleep(5)
```

---

## Expected Results

### Success Criteria
- ✅ Job status: `DONE`
- ✅ Results returned: 25 (or close to 25)
- ✅ Result names are real business names (not empty/null)
- ✅ Results have addresses in Kathmandu
- ✅ No worker errors in logs

### Sample Expected Data

**Restaurants**:
- Bhojan Griha
- Fire and Ice Pizzeria
- Krishnarpan Restaurant
- The Old House Restaurant
- Thamel House Restaurant

**Pharmacies**:
- Kathmandu Pharmacy
- Nepal Pharmacy
- City Pharmacy
- Health Care Pharmacy
- Medical Pharmacy

**Hospitals**:
- Tribhuvan University Teaching Hospital
- Bir Hospital
- Patan Hospital
- Grande International Hospital
- Nepal Mediciti Hospital

---

## Troubleshooting

### If Job Status = FAILED

1. **Check worker logs**:
```bash
docker logs gen_scraper-worker-1 --tail=50
```

2. **Common issues**:
   - Source not active → Already fixed ✅
   - Source not in registry → Already fixed ✅
   - Category name mismatch → Check `_get_category_from_source_name()`
   - Website structure changed → Need to update selectors
   - Network timeout → Increase timeout in scraper

3. **Check error message**:
```bash
docker-compose run --rm -e PYTHONPATH=/app backend python -c "
from database import SessionLocal
from models import ScrapeJob
db = SessionLocal()
job = db.query(ScrapeJob).filter(ScrapeJob.id == 'YOUR_JOB_ID').first()
print(f'Status: {job.status}')
print(f'Error: {job.error_message}')
db.close()
"
```

### If Results = 0

1. **Check if category exists on NepalYP**:
   - Visit: `https://www.nepalyp.com/category/Restaurants/city:Kathmandu`
   - Verify listings appear

2. **Check selector logic**:
   - NepalYP uses: `a[href*="/company/"]` for business links
   - May need to update selectors if website changed

3. **Check logs for extraction errors**:
```bash
docker logs gen_scraper-worker-1 --tail=100 | grep "nepalyp"
```

---

## Next Steps After Verification

### If All Tests Pass ✅
- Document that NepalYP category scrapers work out-of-the-box
- No selector changes needed
- Can proceed to implement other scrapers (Agoda, OYO, etc.)

### If Tests Fail ❌
- Investigate root cause
- Update selectors if website structure changed
- Fix `_get_category_from_source_name()` if category extraction fails
- Update URL pattern if NepalYP changed their URL structure

---

## Test Results

### Test 1: Restaurants
- **Job ID**: _____________
- **Status**: _____________
- **Results Count**: _____________
- **Sample Names**:
  1. _____________
  2. _____________
  3. _____________

### Test 2: Pharmacies
- **Job ID**: _____________
- **Status**: _____________
- **Results Count**: _____________
- **Sample Names**:
  1. _____________
  2. _____________
  3. _____________

### Test 3: Hospitals
- **Job ID**: _____________
- **Status**: _____________
- **Results Count**: _____________
- **Sample Names**:
  1. _____________
  2. _____________
  3. _____________

### Worker Logs
```
[Paste relevant worker logs here]
```

---

**Status**: ⏳ **AWAITING TEST EXECUTION**

Please run the tests and fill in the results above!
