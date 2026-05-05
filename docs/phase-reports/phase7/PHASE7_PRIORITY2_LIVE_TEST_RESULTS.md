# Phase 7 - Priority 2 Live Test Results

**Date:** May 4, 2026  
**Test Type:** Live scraping jobs with new NepalYP sources  
**Worker Status:** Restarted to load updated registry

---

## Issue Discovered & Resolved

### Problem
Initial test jobs (Real Estate & Homestays) only returned Google Maps results, no NepalYP results.

### Root Cause
The Celery worker was running with the old registry.py that didn't include the 7 new NepalYP scrapers. Worker logs showed:
```
scraper.not_found available_scrapers=[...] source_name=nepalyp_real_estate
orchestrator.scraper_not_found error=Unknown scraper: nepalyp_real_estate
```

### Solution
Restarted the Celery worker to pick up the updated registry:
```bash
docker-compose restart worker
```

---

## Test Job Results

### Job 1: Real Estate in Kathmandu (Before Worker Restart)
- **Job ID:** `60a19c3d-e637-4dc8-be40-d49782b43325`
- **Status:** ✅ DONE
- **Max Results:** 10
- **Sources Attempted:**
  - ❌ nepalyp_real_estate - Failed (scraper not found in registry)
  - ✅ google_maps - Success
- **Results:**
  - Google Maps: 10/10 with 100% coordinates
  - NepalYP: 0 (scraper not found)
- **Total:** 10 results

### Job 2: Homestays in Pokhara (Before Worker Restart)
- **Job ID:** `fc16116e-1ead-4694-915e-3c1d12f164b6`
- **Status:** ✅ DONE
- **Max Results:** 10
- **Sources Attempted:**
  - ❌ nepalyp_homestays - Failed (scraper not found in registry)
  - ✅ google_maps - Success
- **Results:**
  - Google Maps: 10/10 with 100% coordinates
  - NepalYP: 0 (scraper not found)
- **Total:** 10 results

### Job 3: Real Estate in Kathmandu (After Worker Restart)
- **Job ID:** `d90779c3-1c17-4c63-8689-edd42d752657`
- **Status:** ✅ DONE
- **Max Results:** 15
- **Sources Attempted:**
  - ✅ nepalyp_real_estate - Success (but returned 0 results)
  - ✅ google_maps - Success
- **Results:**
  - Google Maps: 15/15 with 100% coordinates
  - NepalYP: 0 (scraper ran but found no businesses)
- **Total:** 15 results

---

## NepalYP Real Estate Scraper Analysis

### What Happened
The NepalYP scraper successfully ran but returned 0 results:

```
nepalyp.scrape_start location=Kathmandu max_results=15
nepalyp.scraping_page category=Real_estate page=1 
  url=https://www.nepalyp.com/category/Real_estate/city:Kathmandu
nepalyp.links_found count=1
nepalyp.page_extracted hotels_on_page=0 page=1 total_hotels=0
nepalyp.last_page_reached page=1 total_hotels=0
nepalyp.scrape_complete location=Kathmandu total=0
```

### Possible Reasons
1. **Empty Category:** NepalYP's Real Estate category for Kathmandu might be empty or have very few listings
2. **Selector Mismatch:** The generic NepalYP selectors might not match the Real Estate category page structure
3. **Different Page Layout:** Real Estate listings might use a different HTML structure than Hotels/Restaurants

### Verification Needed
To confirm, we should:
1. Manually visit: https://www.nepalyp.com/category/Real_estate/city:Kathmandu
2. Check if there are actual listings on the page
3. If listings exist, inspect the HTML to see if selectors need adjustment
4. Test with a different category that's known to have data (e.g., nepalyp_tourist_attractions)

---

## Google Maps Results (Job 3)

**Sample Businesses Extracted:**
1. NepalHomes.com (27.6914, 85.3281)
2. Sara Sewa Pvt Ltd (27.7080, 85.3377)
3. Gharbazar (27.6896, 85.3343)
4. Nepal Bhoomi Real Estate Agency (27.7248, 85.3229)
5. नेपाल रियल एस्टेट (27.6661, 85.3140)
6. Eproperty Nepal (27.6920, 85.3392)
7. 99aana (27.6902, 85.3390)
8. Nepal Home Search (27.7061, 85.3268)
9. Mero Ghar Jagga Nepal (27.7040, 85.3332)
10. Kantipur Real Estate (27.6870, 85.3418)
11. Gharsansar: Real Estate in Nepal (27.7126, 85.2834)
12. Fyafulla Real Estate Services (27.7198, 85.3042)
13. Lalpurja Nepal (27.7195, 85.3091)
14. Global International Real Estate (27.7051, 85.3435)
15. Real Estate Of Nepal (27.6977, 85.3314)

**Coordinate Extraction:** 15/15 (100%)

---

## Key Findings

### ✅ Successes
1. **Worker Restart Fixed Registry Issue:** After restart, NepalYP scrapers are now recognized and can run
2. **NepalYP Scraper Executes:** The scraper successfully navigates to NepalYP and attempts to extract data
3. **Google Maps Continues Working:** 100% coordinate extraction rate maintained
4. **No Breaking Changes:** Existing functionality preserved

### ⚠️ Issues to Investigate
1. **NepalYP Real Estate Returns 0 Results:** Need to verify if category is empty or if selectors need adjustment
2. **No NepalYP Data Yet:** Can't verify merging or data quality until we get NepalYP results

### 📋 Next Steps
1. **Test Different Category:** Try nepalyp_tourist_attractions or nepalyp_petrol_stations (categories more likely to have data)
2. **Manual Verification:** Visit NepalYP Real Estate page to confirm if listings exist
3. **Selector Debugging:** If listings exist but aren't extracted, debug the selectors
4. **Complete Priority 2:** Once we confirm at least one NepalYP source returns data, mark Priority 2 as fully complete

---

## Recommendations

### Immediate Action
Create a test job for **Tourist Attractions** or **Petrol Stations** in Kathmandu - these categories are more likely to have active listings on NepalYP.

### If NepalYP Categories Are Empty
This is actually expected for some niche categories. The value of adding these sources is:
1. **Future-Proofing:** When NepalYP adds listings, they'll automatically be scraped
2. **Google Maps Coverage:** Google Maps provides excellent coverage for all categories
3. **Zero Cost:** Adding inactive sources has no performance impact

### Priority 3 Can Proceed
Even without NepalYP data, we can proceed with Priority 3 (Fuzzy Matching) since:
- We have Google Maps data for testing
- We have existing directoryofnepal data
- The fuzzy matching logic is source-agnostic

---

**Report Generated:** May 4, 2026  
**Status:** Worker restarted successfully, NepalYP scrapers now functional  
**Next:** Test additional categories to verify NepalYP data extraction
