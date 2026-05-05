# DirectoryOfNepal Hotels Category Fix - Verification Report

**Date**: May 2, 2026  
**Status**: ✅ FIXED - Ready for Testing

---

## Critical Bug Identified

### The Problem
The Hotels category in DirectoryOfNepal scraper had the **wrong submajorid** in the CATEGORY_MAP:

```python
# WRONG (was scraping Emergency Health Services instead of Hotels)
"hotels": ("Hotels", 1, None)  # submajorid=1 = Emergency Health Services
```

This caused the previous Hotels test job to scrape **hospitals** instead of **hotels**.

### The Fix
Updated CATEGORY_MAP to use the correct submajorid for Hotels & Resorts:

```python
# CORRECT (now scrapes actual Hotels & Resorts)
"hotels": ("Hotels & Resorts", 213, None)  # submajorid=213 = Hotels & Resorts
```

### URL Comparison

**Before (Wrong)**:
```
https://www.directoryofnepal.com/category.php?submajorid=1&submajorname=Hotels&district=Kathmandu
→ This scraped Emergency Health Services (hospitals, clinics)
```

**After (Correct)**:
```
https://www.directoryofnepal.com/category.php?submajorid=213&submajorname=Hotels+%26+Resorts&district=Kathmandu
→ This scrapes actual Hotels & Resorts (929 hotels in Kathmandu)
```

---

## Changes Applied

### 1. Fixed CATEGORY_MAP in `backend/scrapers/directoryofnepal.py`
- Changed Hotels submajorid from `1` to `213`
- Changed Hotels submajorname from `"Hotels"` to `"Hotels & Resorts"`
- Updated docstring to reflect correct submajorid

### 2. Updated Unit Tests in `backend/tests/test_directoryofnepal.py`
- Fixed `test_directoryofnepal_scraper_category_extraction_hotels()` assertions
- Fixed `test_directoryofnepal_scraper_category_extraction_default()` assertions
- Both now expect `"Hotels & Resorts"` and `submajorid=213`

### 3. Restarted Services
- Backend and worker services restarted to pick up changes
- All services running healthy

---

## Test Results

### Unit Tests: ✅ ALL PASSING
```
18 passed, 2 warnings in 54.75s
```

All DirectoryOfNepal tests pass with the corrected category mapping.

---

## Next Steps: Create New Test Job

### Step 1: Create Test Job via Frontend
Go to http://localhost:5173/dashboard and create a new job:

- **Category**: Hotels
- **Source**: directoryofnepal_hotels
- **Location**: Kathmandu
- **Limit**: 10

### Step 2: Verify Results Are Real Hotels
After job completes, check the database:

```bash
docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c \
  "SELECT name, city, phone_primary, website FROM cleaned_results WHERE source_id=(SELECT id FROM sources WHERE name='directoryofnepal_hotels') ORDER BY created_at DESC LIMIT 5;"
```

**Expected Results**: Real hotel names like:
- Kathmandu Boutique Cottage
- Hotel Mirage Regency
- Hotel Shanker
- Hyatt Regency Kathmandu
- Radisson Hotel Kathmandu

**NOT Expected**: Hospital names like:
- Kathmandu Medical College
- Nepal Mediciti Hospital
- Grande International Hospital

### Step 3: Check Worker Logs
```bash
docker logs gen_scraper-worker-1 --tail=100 | grep -i "directoryofnepal\|error\|failed"
```

Look for:
- Correct URL with `submajorid=213`
- No errors during scraping
- Successful completion message

---

## Summary

✅ **Bug Fixed**: Hotels category now uses correct submajorid (213 instead of 1)  
✅ **Tests Updated**: All 18 unit tests passing  
✅ **Services Restarted**: Backend and worker running with new code  
⏳ **Pending**: Create new test job to verify real hotel data is scraped

---

## Previous Job Data (Wrong Category)

The previous Hotels job (created before the fix) scraped hospitals instead of hotels because it used `submajorid=1`. That data should be ignored or deleted as it's from the wrong category.

To verify the old job scraped hospitals, you can check:
```bash
docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c \
  "SELECT name FROM cleaned_results WHERE source_id=(SELECT id FROM sources WHERE name='directoryofnepal_hotels') ORDER BY created_at ASC LIMIT 5;"
```

If you see hospital names, those are from the buggy version.
