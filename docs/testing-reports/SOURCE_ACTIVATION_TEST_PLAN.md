# Source Activation & Testing Plan

**Date**: May 3, 2026  
**Status**: All 26 sources activated, ready for testing

---

## ✅ Step 1: All Sources Activated

Successfully activated all 26 sources in the database:
- Previously: 15 active, 11 inactive
- Now: **26 active sources**

---

## 🧪 Step 2: Test Plan - Verify 3 Sources

We'll test these 3 sources to verify they return actual data:

### Sources to Test:

1. **Booking.com** (ID: 2)
   - Status: ✅ Already proven working (50 results from yesterday)
   - Expected: Should return 5+ hotel results

2. **DirectoryOfNepal Hotels** (ID: 12)
   - Status: 🆕 Recently implemented
   - Expected: Should return 5+ hotel results from directoryofnepal.com

3. **NepalYP Hospitals** (ID: 9)
   - Status: 🆕 NepalYP category scraper
   - Expected: Should return 5+ hospital results from nepalyp.com

---

## 📋 How to Test (Manual via Frontend)

### Option A: Test All 3 Together

1. **Go to Dashboard**: http://localhost:5173/dashboard
2. **Click "Create New Job"**
3. **Fill in the form**:
   - Location: `Kathmandu`
   - Category: `Hotels`
   - Sources: Select these 3:
     - ☑️ Booking.com
     - ☑️ DirectoryOfNepal Hotels
     - ☑️ NepalYP Hospitals
   - Max Results: `5`
4. **Click "Start Scraping"**
5. **Monitor the job** - it will show progress for each source
6. **Check results** when status = DONE

### Option B: Test One at a Time

Test each source individually to isolate any issues:

**Test 1: Booking.com**
- Location: Kathmandu
- Category: Hotels
- Source: Booking.com only
- Expected: 5 results with hotel names, addresses, ratings

**Test 2: DirectoryOfNepal Hotels**
- Location: Kathmandu
- Category: Hotels  
- Source: DirectoryOfNepal Hotels only
- Expected: 5 results with hotel names, addresses, phones

**Test 3: NepalYP Hospitals**
- Location: Kathmandu
- Category: Hospitals
- Source: NepalYP Hospitals only
- Expected: 5 results with hospital names, addresses, phones

---

## 🔍 What to Look For

### Success Indicators ✅
- Job status changes to "DONE"
- Results count > 0 for each source
- Results have actual data (names, addresses, etc.)
- No error messages in job details

### Failure Indicators ❌
- Job status = "FAILED"
- Results count = 0
- Error messages like:
  - "No results found"
  - "Selector not found"
  - "Connection timeout"
  - "Page not found"

---

## 📊 Check Results in Monitoring Dashboard

After running test jobs:

1. **Go to**: http://localhost:5173/admin/monitoring
2. **Check "Scraper Health" table**:
   - All 3 sources should show "Active" status
   - Last Job Status should be "DONE" (if successful)
   - Result Count should be > 0

3. **Check "Results Per Source" chart**:
   - Should see bars for the 3 tested sources

4. **Check "Recent Failures" table**:
   - Should be empty if all tests passed
   - If failures exist, check error messages

---

## 🐛 Troubleshooting

### If Booking.com Fails:
- Check if selectors need updating (website may have changed)
- Check backend logs: `docker-compose logs backend | grep -i booking`

### If DirectoryOfNepal Fails:
- Verify the website is accessible: https://directoryofnepal.com/hotels/
- Check if selectors are correct
- Check backend logs: `docker-compose logs backend | grep -i directory`

### If NepalYP Fails:
- Verify the website is accessible: https://www.nepalyp.com/
- Check if category URL mapping is correct
- Check backend logs: `docker-compose logs backend | grep -i nepalyp`

---

## 📝 Expected Results Summary

| Source | Category | Expected Count | Expected Data |
|--------|----------|----------------|---------------|
| Booking.com | Hotels | 5+ | Name, address, rating, price, image |
| DirectoryOfNepal Hotels | Hotels | 5+ | Name, address, phone, email |
| NepalYP Hospitals | Hospitals | 5+ | Name, address, phone, website |

---

## 🎯 Next Steps After Testing

### If All 3 Pass ✅
- All sources are working correctly
- System is ready for production use
- Can proceed with testing other categories

### If Some Fail ❌
- Identify which sources failed
- Check error messages
- Update selectors if needed
- Re-test failed sources

### If All Fail ❌
- Check if worker is running: `docker-compose ps worker`
- Check worker logs: `docker-compose logs worker`
- Verify database connection
- Check if Celery is processing tasks

---

## 🔧 Quick Commands

**Check worker status**:
```bash
docker-compose ps worker
```

**View worker logs**:
```bash
docker-compose logs -f worker
```

**View backend logs**:
```bash
docker-compose logs -f backend
```

**Check database for results**:
```bash
docker-compose exec postgres psql -U scraper -d scraper_db -c "SELECT s.display_name, COUNT(r.id) FROM sources s LEFT JOIN raw_results r ON s.id = r.source_id WHERE s.id IN (2, 9, 12) GROUP BY s.display_name;"
```

---

**Ready to test!** Go to http://localhost:5173/dashboard and create your first test job! 🚀

