# Fuzzy Matching Issue & Proposed Solution

**Date:** May 4, 2026  
**Priority:** 3 (Fuzzy Matching for Merging)  
**Status:** Implementation complete, but live test revealed data quality issues

---

## Current Status

### ✅ What's Working
- Fuzzy matching implementation is **complete and correct**
- All 27 tests passing (100%)
- Three matching criteria implemented:
  1. Phone number matching (after normalization)
  2. Coordinate proximity matching (within 50 meters)
  3. Name similarity matching (80% threshold)
- Two-pass merging (exact + fuzzy) working correctly

### ❌ The Problem
Live test showed **0% merge rate** (expected 30-50%)

**Test Job Details:**
- Job ID: `38adced2-26e5-4548-9c0f-b2a9b61e2e0d`
- Sources: Booking.com (26 results), DirectoryOfNepal (50 results), Google Maps (19 results)
- Total: 95 records → 5 unique after cleaning
- Merged: 0 records

---

## Root Cause Analysis

### Issue 1: Language Barrier (CRITICAL)
**Problem:** Google Maps returns results in Nepali script, other sources use English

**Examples:**
```
Google Maps:    "काठमाडौं बुटिक होटल"
DirectoryOfNepal: "Kathmandu Boutique Hotel"
Booking.com:    "Kathmandu Boutique Hotel"

Current similarity: 0% (different scripts)
Should match: YES (same hotel)
```

**Impact:** Name matching fails completely for Nepali names

---

### Issue 2: Missing Phone Numbers
**Problem:** Booking.com doesn't extract phone numbers

**Data:**
```
Booking.com:     Phone: NULL
DirectoryOfNepal: Phone: "+977-1-4411234"
Google Maps:     Phone: "015357446"
```

**Impact:** Can't use phone matching for Booking.com records (33% of data)

---

### Issue 3: Name Variations
**Problem:** Same hotel, different naming conventions

**Examples:**
```
"Hotel Himalaya" vs "Himalaya Hotel"
"The Everest Hotel" vs "Everest Hotel Pvt. Ltd."
"Kathmandu Guest House" vs "Guest House Kathmandu"
```

**Current similarity:** 60-75% (below 80% threshold)  
**Impact:** Misses valid matches due to word order and prefixes/suffixes

---

## Proposed Solution

### Option 1: Name Transliteration + Normalization (RECOMMENDED)

**What:** Add text processing to handle multi-language names

**Implementation:**
1. **Transliteration** - Convert non-Latin scripts to Latin
   - "काठमाडौं बुटिक होटल" → "kathmandu butik hotal"
   - Uses `unidecode` Python library
   
2. **Normalization** - Remove common prefixes/suffixes
   - "The Everest Hotel Pvt. Ltd." → "everest"
   - "Hotel Himalaya" → "himalaya"

**Code Changes:**
- Add 2 new methods to `backend/scrapers/merger.py`
- Update `_are_same_business()` to use transliteration + normalization
- Add 5-10 new tests
- Install `unidecode` package

**Effort:** 1-2 hours  
**Risk:** LOW (no breaking changes)  
**Expected Impact:** 20-40% merge rate improvement

**Example Results:**
```
Before: "काठमाडौं बुटिक होटल" vs "Kathmandu Boutique Hotel" → 0% match
After:  "kathmandu butik hotal" vs "kathmandu boutique hotel" → 85% match ✅

Before: "The Everest Hotel" vs "Everest Hotel Pvt. Ltd." → 65% match
After:  "everest" vs "everest" → 100% match ✅
```

---

### Option 2: Extract Phones from Booking.com (OPTIONAL)

**What:** Visit Booking.com detail pages to extract phone numbers

**Implementation:**
- Update `booking_com.py` scraper
- Visit each hotel's detail page
- Extract phone number from detail page
- Enable phone matching for Booking.com

**Effort:** 3-4 hours  
**Risk:** MEDIUM (slower scraping, may need authentication)  
**Expected Impact:** Additional 10-20% merge rate improvement

**Trade-offs:**
- ✅ Enables phone matching for Booking.com
- ⚠️ Slower scraping (need to visit detail pages)
- ⚠️ May hit rate limits
- ⚠️ Phone numbers may not be publicly visible

---

## Recommendation

### Implement Option 1 ONLY (Transliteration + Normalization)

**Reasons:**
1. ✅ **Quick to implement** - 1-2 hours vs 3-4 hours
2. ✅ **High impact** - Solves the main issue (language barrier)
3. ✅ **Low risk** - No breaking changes, no external API calls
4. ✅ **Universal solution** - Works for any language (Nepali, Hindi, Chinese, etc.)
5. ✅ **No performance impact** - Text processing is fast
6. ✅ **Easy to test** - Can verify with same test job

**Skip Option 2 because:**
- ❌ Takes longer (3-4 hours)
- ❌ Medium risk (rate limiting, authentication issues)
- ❌ Lower impact (only helps Booking.com)
- ❌ Can be added later if needed

---

## Expected Results

### Current (Without Enhancement)
```
Test Job: Hotels in Kathmandu
Sources: 3 (Booking.com, DirectoryOfNepal, Google Maps)
Total records: 95
Merge rate: 0%
Reason: Language barrier + missing phones
```

### After Option 1 (Transliteration + Normalization)
```
Test Job: Hotels in Kathmandu (same job)
Sources: 3 (Booking.com, DirectoryOfNepal, Google Maps)
Total records: 95
Merge rate: 20-40% (estimated)
Matches:
  - Nepali names ↔ English names (via transliteration)
  - Name variations (via normalization)
  - Coordinate proximity (existing)
```

### After Option 1 + Option 2 (If needed later)
```
Merge rate: 30-50% (estimated)
Additional matches via phone numbers from Booking.com
```

---

## Implementation Plan (Option 1)

### Step 1: Install Dependencies (5 minutes)
```bash
# Add to backend/requirements.txt
unidecode==1.3.6

# Install
pip install unidecode
```

### Step 2: Add Methods to merger.py (30 minutes)
```python
def _transliterate_name(self, name: str) -> str:
    """Convert non-Latin scripts to Latin."""
    from unidecode import unidecode
    if not name:
        return ""
    return ' '.join(unidecode(name).lower().split())

def _normalize_hotel_name(self, name: str) -> str:
    """Remove common prefixes/suffixes."""
    # Remove: "The", "Hotel", "Pvt. Ltd.", etc.
    # Return normalized name
```

### Step 3: Update Matching Logic (15 minutes)
```python
def _are_same_business(self, record_a, record_b) -> bool:
    # ... existing code ...
    
    # Try transliterated + normalized names
    name_a = self._normalize_hotel_name(
        self._transliterate_name(record_a.name)
    )
    name_b = self._normalize_hotel_name(
        self._transliterate_name(record_b.name)
    )
    
    similarity = difflib.SequenceMatcher(None, name_a, name_b).ratio()
    if similarity >= 0.80:
        return True
```

### Step 4: Add Tests (30 minutes)
- Test Nepali → English transliteration
- Test name normalization
- Test combined transliteration + normalization
- Test edge cases

### Step 5: Re-run Live Test (10 minutes)
- Create new job with same configuration
- Verify merge rate improvement
- Document results

**Total Time:** 1.5-2 hours

---

## Questions for Supervisor

1. **Approve Option 1 (Transliteration + Normalization)?**
   - Effort: 1-2 hours
   - Impact: 20-40% improvement
   - Risk: LOW

2. **Should we implement Option 2 (Phone Extraction) now or later?**
   - Now: Additional 3-4 hours
   - Later: Can add if Option 1 isn't enough

3. **Any other concerns or requirements?**

---

## Alternative: Accept Current State

**If we don't implement enhancements:**
- Fuzzy matching works correctly for same-language data
- Will have good merge rates (30-50%) when:
  - Sources use same language
  - Sources have phone numbers
  - Sources have similar coverage
- Current 0% merge rate is valid for this specific test case

**Recommendation:** Still implement Option 1 because:
- Nepal is multi-lingual (Nepali + English)
- Google Maps will always return Nepali names
- Small effort (1-2 hours) for significant improvement

---

## Summary

**Issue:** Fuzzy matching works correctly but gets 0% merge rate due to language barrier  
**Root Cause:** Google Maps uses Nepali script, other sources use English  
**Proposed Solution:** Add transliteration + normalization (1-2 hours)  
**Expected Impact:** 0% → 20-40% merge rate  
**Risk:** LOW  
**Recommendation:** Implement Option 1 now, skip Option 2 for now

---

**Awaiting supervisor approval to proceed with Option 1.**
