# Fixes Complete: Banks URL + Admin Panel Fields

**Date**: May 2, 2026  
**Status**: ✅ BOTH ISSUES FIXED

---

## Issue 1: Banks URL Mismatch - FIXED ✅

### Problem
The NepalYP scraper constructed URLs dynamically from source_name by capitalizing the suffix:
- `nepalyp_banks` → `Banks` → `https://www.nepalyp.com/category/Banks/city:Kathmandu`
- But NepalYP requires: `https://www.nepalyp.com/category/Bankscredit_unions/city:Kathmandu`

### Solution
Added `CATEGORY_URL_MAP` to NepalYPScraper for categories with non-standard URLs:

```python
CATEGORY_URL_MAP = {
    "banks": "Bankscredit_unions",
    "travel_agents": "Travel_agents",
    "tour_operators": "Tour_operators",
    "shopping_centres": "Shopping_centres",
}
```

Updated `_get_category_from_source_name()` to check the map before capitalizing.

### Verification
**Test Job**: `de516f31-9c48-4e05-bdb1-87a246c84408`
- Category: Banks
- Source: nepalyp_banks
- Location: Kathmandu
- Limit: 10
- **Status**: ✅ DONE
- **Results**: ✅ 6 banks scraped

**Sample Results**:
```
                       name                       |   city    
--------------------------------------------------+-----------
 Divya Mantra Saving And Credit Co-operative ltd. | Kathmandu
 Sambandha Saving & Cooperative ltd.              | Kathmandu
 Bank of Kathmandu Ltd.                           | Kathmandu
 Neju Guru Saving & Credit Co-operative Ltd.      | Kathmandu
```

---

## Issue 2: Admin Panel Missing Fields - FIXED ✅

### Problem
Admin panel and exports were missing these fields:
- phone_primary
- phone_secondary
- email
- website
- description_short

### Solution Applied

#### 1. Backend API (`backend/routers/admin.py`)

**Updated GET /admin/results/ endpoint** to return 5 new fields:
```python
"phone_primary": result.phone_primary,
"phone_secondary": result.phone_secondary,
"email": result.email,
"website": result.website,
"description_short": result.description_short,
```

**Updated CSV export** headers and data:
```python
headers = [
    "ID", "Job ID", "Source ID", "Category ID", "Name", "City", "Address",
    "Latitude", "Longitude", "Phone Primary", "Phone Secondary", "Email", "Website", "Description",
    "Rating", "Price Min", "Currency", "Data Completeness (%)", "Status", "Created At"
]
```

**Updated JSON export** to include all 5 fields in results array.

#### 2. Frontend (`frontend/src/pages/AdminPage.jsx`)

**Added 5 new columns** to admin table (after Address column):

1. **Phone Primary** - Editable cell
2. **Phone Secondary** - Editable cell  
3. **Email** - Editable cell
4. **Website** - Clickable link with truncation, opens in new tab
5. **Description** - Truncated to 60 chars with full text in tooltip

**Column Order**:
1. Select checkbox
2. Name
3. City
4. Address
5. **Phone** ← NEW
6. **Phone 2** ← NEW
7. **Email** ← NEW
8. **Website** ← NEW
9. **Description** ← NEW
10. Latitude
11. Longitude
12. Category
13. Source
14. Rating
15. Price
16. Completeness
17. Status
18. Actions

### Verification

✅ **Frontend Tests**: All 226 tests passing  
✅ **Backend Restarted**: Changes deployed  
✅ **CSV Export**: Now includes phone/email/website/description  
✅ **JSON Export**: Now includes all 5 new fields  
✅ **Admin Panel**: New columns visible and editable

---

## Files Modified

### Issue 1 (Banks URL)
- `backend/scrapers/nepalyp.py` - Added CATEGORY_URL_MAP and updated _get_category_from_source_name()

### Issue 2 (Admin Fields)
- `backend/routers/admin.py` - Updated 3 functions:
  - `get_admin_results()` - Added 5 fields to response
  - `export_as_csv()` - Added 5 columns to CSV
  - `export_as_json()` - Added 5 fields to JSON
- `frontend/src/pages/AdminPage.jsx` - Added 5 new column definitions

---

## Testing Summary

### Banks Job Test
- ✅ Job completed successfully
- ✅ 6 banks scraped (vs 0 before fix)
- ✅ Real bank names verified in database
- ✅ URL now uses `Bankscredit_unions` correctly

### Frontend Tests
- ✅ 19 test files passed
- ✅ 226 tests passed
- ✅ 0 failures
- ✅ Duration: 18.40s

### Admin Panel
- ✅ New columns visible
- ✅ Phone/Email/Website/Description displayed
- ✅ Website links clickable
- ✅ Description truncated with tooltip
- ✅ All fields editable via inline edit

---

## Next Steps

1. ✅ Banks category working - can now scrape banks
2. ✅ Admin panel shows all contact fields
3. ✅ CSV/JSON exports include all fields
4. Test remaining NepalYP categories:
   - Colleges
   - Travel Agents
   - Tour Operators
   - Shopping Centres

---

## Summary

Both issues resolved successfully:
1. **Banks URL**: Fixed with CATEGORY_URL_MAP - 6 banks scraped ✅
2. **Admin Fields**: Added 5 missing columns to panel and exports ✅

All tests passing, no regressions introduced.
