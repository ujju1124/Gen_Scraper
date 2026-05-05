# Admin Panel Data Explanation

**Date**: May 2, 2026  
**Question**: Why are phone/email/website fields blank in the admin panel?

---

## Current Situation

### ✅ Database Schema
The database **DOES have** the new columns:
- `phone_primary`
- `phone_secondary`
- `email`
- `website`
- `description_short`

### ✅ Frontend Display
The admin panel **DOES show** all 5 new columns in the table.

### ❌ Data Values
The existing scraped data **DOES NOT have** phone/email/website values because:

---

## Why Data is Blank

### 1. **Test Data Source**
Current pharmacy data in the database came from **"fake_source"** (test data):
```sql
SELECT name, source_name FROM cleaned_results 
JOIN sources ON source_id = sources.id 
WHERE category_id = 9;

-- Result: All 21 pharmacies show source_name = 'fake_source'
```

This test data was created **before** we added phone/email/website support, so it only has:
- ✅ Name
- ✅ City  
- ✅ Address
- ❌ Phone (NULL)
- ❌ Email (NULL)
- ❌ Website (NULL)

### 2. **Scraper Capabilities**

Not all scrapers extract contact information:

| Scraper | Phone | Email | Website | Description |
|---------|-------|-------|---------|-------------|
| **directoryofnepal** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |
| **nepalyp** | ❌ No | ❌ No | ❌ No | ❌ No |
| **booking_com** | ❌ No | ❌ No | ❌ No | ❌ No |
| **agoda** | ❌ No | ❌ No | ❌ No | ❌ No |

**Only directoryofnepal scraper** extracts phone/email/website data using a two-pass approach:
- **Pass 1**: Collect listing names and URLs
- **Pass 2**: Visit each detail page to extract phone, email, website

---

## How to Get Data with Contact Info

### Option 1: Run DirectoryOfNepal Scraper ✅ RECOMMENDED

Create a new scrape job using the **directoryofnepal_pharmacies** source:

1. Go to Dashboard
2. Click "Create New Job"
3. Select:
   - **Category**: Pharmacies
   - **Source**: directoryofnepal_pharmacies
   - **Location**: Kathmandu
   - **Max Results**: 20
4. Click "Start Scraping"

**Expected Result**: New pharmacy records with phone/email/website data

### Option 2: Re-scrape Existing Categories

Run new jobs for:
- **directoryofnepal_hotels** (will have phone/email/website)
- **directoryofnepal_restaurants** (will have phone/email/website)
- **directoryofnepal_pharmacies** (will have phone/email/website)

### Option 3: Keep Existing Data

The blank fields are **editable** in the admin panel:
- Click "Click to add" in any phone/email/website cell
- Manually enter the information
- Data will be saved to the database

---

## Verification Steps

After running a directoryofnepal scrape job:

1. **Check Database**:
```bash
docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c \
  "SELECT name, phone_primary, email, website FROM cleaned_results \
   WHERE source_id=(SELECT id FROM sources WHERE name='directoryofnepal_pharmacies') \
   LIMIT 5;"
```

2. **Check Admin Panel**:
   - Go to http://localhost:5173/admin
   - Filter by Source: "DirectoryOfNepal Pharmacies"
   - Verify phone/email/website columns have values

---

## Summary

| Item | Status |
|------|--------|
| Database columns exist | ✅ Yes |
| Frontend displays columns | ✅ Yes |
| Existing data has values | ❌ No (test data) |
| Scraper can extract data | ✅ Yes (directoryofnepal) |
| **Action Required** | **Run new scrape job with directoryofnepal source** |

**The admin panel is working correctly. You just need to scrape data from a source that extracts contact information (directoryofnepal).**
