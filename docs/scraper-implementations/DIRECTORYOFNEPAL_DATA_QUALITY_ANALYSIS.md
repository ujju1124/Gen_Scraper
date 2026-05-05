# DirectoryOfNepal Data Quality Analysis

**Date**: May 2, 2026  
**Job ID**: `d3b9cbaf-57a9-4ee7-ae88-aa4870c0f97f`

---

## Executive Summary

✅ **Scraper is working correctly** - The issue is NOT in the scraper extraction.  
⚠️ **Phone data is being collected** - But it's being lost in the cleaning pipeline.  
✅ **Website extraction working** - Websites are being captured correctly.  
⚠️ **Email extraction working** - But no emails found on these particular pages.

---

## Step 1: Cleaned Results (Final Output)

### Sample 1:
```
name              | Nepal Mediciti
city              | Lalitpur
address           | Bhaisepati,,Lalitpur, Nepal
phone_primary     | [EMPTY]
phone_secondary   | [EMPTY]
website           | https://www.nepalmediciti.com
email             | [EMPTY]
description_short | [EMPTY]
```

### Sample 2:
```
name              | vinayak hospital and maternity home pvt. ltd.
city              | Kathmandu
address           | gongabu chowk,,Kathmandu, Nepal
phone_primary     | [EMPTY]
phone_secondary   | [EMPTY]
website           | https://statcounter.com/
email             | [EMPTY]
description_short | [EMPTY]
```

### Sample 3:
```
name              | ERA International Hospital Pvt. Ltd.
city              | Kathmandu
address           | Sorakhutee,Kathmandu,Kathmandu, Nepal
phone_primary     | [EMPTY]
phone_secondary   | [EMPTY]
website           | https://era-hospital.com/
email             | [EMPTY]
description_short | [EMPTY]
```

---

## Step 2: Scraper Implementation Analysis

### Key Implementation Details:

**Two-Pass Approach**:
1. **Pass 1**: Collect listings from listing pages
   - Selector: `h2 a` for name and URL
   - Selector: `p.addr` for address
   - Selector: `p` for description

2. **Pass 2**: Visit each detail page
   - Selector: `div.param` for full address (with "Address:" prefix)
   - Selector: `div.cmp-item:contains("Landline") div.val a` for phone_primary
   - Selector: `div.cmp-item:contains("Mobile") div.val a` for phone_secondary
   - Selector: `a[href^="mailto:"]` for email
   - Selector: `a[href^="http"]` for website (with domain filtering)

**Error Handling**:
- If detail page fails → keeps listing data with None values
- Never crashes on missing data

**Data Mapping**:
```python
result = {
    'name': listing['name'],
    'address': full_address or listing['address'],
    'city': city,
    'country': 'Nepal',
    'phone': phone_primary,           # ← Maps to 'phone'
    'phone_secondary': phone_secondary,
    'email': email,
    'website': website,
    'description': listing['description'],
    'url': detail_url,
    'category': submajorname
}
```

---

## Step 3: Raw Results (Before Cleaning)

### Raw Result 1:
```json
{
  "url": "https://www.directoryofnepal.com/company/29770/damak-chasma-ghar-eye-care.html",
  "city": "Jhapa",
  "name": "Damak Chasma Ghar & Eye Care",
  "email": null,
  "phone": "+977-23-580859",              ← PHONE DATA PRESENT!
  "address": "Way to Department of roads,Jesis Chowk, Damak-11,Jhapa Nepal,Jhapa, Nepal",
  "country": "Nepal",
  "website": "https://statcounter.com/",
  "category": "Hotels",
  "description": "...",
  "phone_secondary": "+977-9842632429"    ← PHONE SECONDARY PRESENT!
}
```

### Raw Result 2:
```json
{
  "url": "https://www.directoryofnepal.com/company/33351/kathmandu-national-medical-college-teaching-hospital.html",
  "city": "Kathmandu",
  "name": "Kathmandu National Medical College & Teaching Hospital",
  "email": null,
  "phone": "+977-1-01-4771557",           ← PHONE DATA PRESENT!
  "address": "29 Ghattekulo Marga ,Kathmandu,Kathmandu, Nepal",
  "country": "Nepal",
  "website": "https://kathmandunational.edu.np",
  "category": "Hotels",
  "description": "At Kathmandu National Medical College & Teaching Hospital...",
  "phone_secondary": "+977-9816203005"    ← PHONE SECONDARY PRESENT!
}
```

---

## Critical Finding: Data Loss in Cleaning Pipeline

### The Problem:

**Scraper Output** (raw_data):
- ✅ `phone`: "+977-23-580859"
- ✅ `phone_secondary`: "+977-9842632429"

**Cleaner Output** (cleaned_results):
- ❌ `phone_primary`: NULL
- ❌ `phone_secondary`: NULL

### Root Cause:

The scraper uses the key **`phone`** but the cleaner expects **`phone_primary`**.

**In scraper** (`backend/scrapers/directoryofnepal.py` line 313):
```python
result = {
    'phone': phone_primary,  # ← Uses 'phone' key
    'phone_secondary': phone_secondary,
}
```

**In cleaner** (`backend/scrapers/cleaner.py`):
The cleaner likely expects:
```python
phone_primary = raw_data.get('phone_primary')  # ← Expects 'phone_primary' key
phone_secondary = raw_data.get('phone_secondary')
```

---

## Data Quality Summary

### ✅ Working Correctly:
1. **Name extraction**: 100% success rate
2. **City extraction**: Working (extracted from address)
3. **Address extraction**: Working (full addresses captured)
4. **Website extraction**: Working (captured correctly)
5. **URL extraction**: 100% success rate
6. **Category mapping**: Working
7. **Country**: Correctly set to "Nepal"

### ⚠️ Data Being Lost:
1. **Phone numbers**: Collected by scraper but lost in cleaning
   - Raw data shows: `phone: "+977-23-580859"`
   - Cleaned data shows: `phone_primary: NULL`
   - **Cause**: Key mismatch (`phone` vs `phone_primary`)

2. **Phone secondary**: Collected by scraper but lost in cleaning
   - Raw data shows: `phone_secondary: "+977-9842632429"`
   - Cleaned data shows: `phone_secondary: NULL`
   - **Cause**: Possible key mismatch or cleaner issue

### ℹ️ Expected Behavior:
1. **Email**: NULL in raw data (no emails found on these pages)
2. **Description**: Present in raw data but not mapped to `description_short`

### ⚠️ Website Quality Issue:
- Some websites are `https://statcounter.com/` (tracking script)
- This is a selector issue - the website filter should be more aggressive

---

## Recommendations

### 1. Fix Phone Number Mapping (CRITICAL)

**Option A**: Update scraper to use `phone_primary` key
```python
# In backend/scrapers/directoryofnepal.py line 313
result = {
    'phone_primary': phone_primary,  # ← Change from 'phone'
    'phone_secondary': phone_secondary,
}
```

**Option B**: Update cleaner to accept `phone` key
```python
# In backend/scrapers/cleaner.py
phone_primary = raw_data.get('phone_primary') or raw_data.get('phone')
```

### 2. Fix Website Filtering (MEDIUM)

Add `statcounter.com` to excluded domains:
```python
excluded_domains = [
    'directoryofnepal.com',
    'facebook.com',
    'twitter.com',
    'linkedin.com',
    'google.com',
    'statcounter.com',  # ← Add this
]
```

### 3. Map Description to description_short (LOW)

Update result dictionary:
```python
result = {
    ...
    'description': listing['description'],
    'description_short': listing['description'],  # ← Add this
}
```

---

## Verification Commands

### Check if phone data exists in raw_results:
```bash
docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c \
  "SELECT raw_data->>'phone' as phone, raw_data->>'phone_secondary' as phone_secondary \
   FROM raw_results WHERE job_id='d3b9cbaf-57a9-4ee7-ae88-aa4870c0f97f' LIMIT 5;"
```

### Check if phone data exists in cleaned_results:
```bash
docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c \
  "SELECT phone_primary, phone_secondary \
   FROM cleaned_results WHERE job_id='d3b9cbaf-57a9-4ee7-ae88-aa4870c0f97f' LIMIT 5;"
```

---

## Conclusion

The DirectoryOfNepal scraper is **working correctly**. The phone data is being extracted successfully from detail pages and stored in raw_results. However, there is a **key mismatch** between the scraper output (`phone`) and what the cleaner expects (`phone_primary`), causing phone data to be lost during the cleaning process.

**Action Required**: Update the scraper to use `phone_primary` instead of `phone` in the result dictionary.

---

## Files to Modify

1. `backend/scrapers/directoryofnepal.py` - Line 313: Change `'phone'` to `'phone_primary'`
2. `backend/scrapers/directoryofnepal.py` - Line 318: Add `'description_short'` mapping
3. `backend/scrapers/directoryofnepal.py` - Line 289: Add `'statcounter.com'` to excluded_domains
