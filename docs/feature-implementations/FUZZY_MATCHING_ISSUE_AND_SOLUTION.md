# Fuzzy Matching Issue & Proposed Solution

**Date:** May 4, 2026  
**Priority:** 3 (Fuzzy Matching for Merging)  
**Status:** Implementation complete, 0% merge rate in live test

---

## The Problem

Live test showed **0% merge rate** (expected 30-50%)

**Test Job:**
- Job ID: `38adced2-26e5-4548-9c0f-b2a9b61e2e0d`
- Sources: Booking.com (26), DirectoryOfNepal (50), Google Maps (19)
- Total: 95 records → 5 unique after cleaning
- **Merged: 0 records**

---

## Root Cause

### Issue 1: Language Barrier (CRITICAL)
Google Maps returns Nepali script, other sources use English:

```
Google Maps:      "काठमाडौं बुटिक होटल"
DirectoryOfNepal: "Kathmandu Boutique Hotel"
Booking.com:      "Kathmandu Boutique Hotel"

Current similarity: 0% ❌
Should match: YES (same hotel)
```

### Issue 2: Missing Phone Numbers
Booking.com doesn't extract phone numbers (33% of data has no phones)

### Issue 3: Name Variations
```
"Hotel Himalaya" vs "Himalaya Hotel"
"The Everest Hotel" vs "Everest Hotel Pvt. Ltd."

Current similarity: 60-75% (below 80% threshold) ❌
```

---

## My Proposed Solution

### Add Transliteration + Normalization

**What it does:**
1. **Transliteration** - Convert non-Latin scripts to Latin
   - "काठमाडौं बुटिक होटल" → "kathmandu butik hotal"
   
2. **Normalization** - Remove common prefixes/suffixes
   - "The Everest Hotel Pvt. Ltd." → "everest"
   - "Hotel Himalaya" → "himalaya"

**Implementation:**

```python
# Add to backend/scrapers/merger.py

from unidecode import unidecode

def _transliterate_name(self, name: str) -> str:
    """Convert non-Latin scripts to Latin."""
    if not name:
        return ""
    return ' '.join(unidecode(name).lower().split())

def _normalize_hotel_name(self, name: str) -> str:
    """Remove common prefixes/suffixes."""
    if not name:
        return ""
    
    normalized = name.lower()
    
    # Remove prefixes
    prefixes = ['the ', 'hotel ', 'resort ', 'guest house ']
    for prefix in prefixes:
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix):]
    
    # Remove suffixes
    suffixes = [
        ' hotel', ' resort', ' guest house', ' pvt. ltd.', ' pvt ltd',
        ' ltd.', ' ltd', ' & spa', ' and spa', ' inn', ' lodge'
    ]
    for suffix in suffixes:
        if normalized.endswith(suffix):
            normalized = normalized[:-len(suffix)]
    
    return ' '.join(normalized.split())

def _are_same_business(self, record_a, record_b) -> bool:
    # ... existing safety checks ...
    
    # Name fuzzy match with transliteration + normalization
    if record_a.name and record_b.name:
        # Transliterate + normalize both names
        name_a = self._normalize_hotel_name(
            self._transliterate_name(record_a.name)
        )
        name_b = self._normalize_hotel_name(
            self._transliterate_name(record_b.name)
        )
        
        similarity = difflib.SequenceMatcher(None, name_a, name_b).ratio()
        if similarity >= 0.80:
            logger.debug(
                "merger.fuzzy_match_name_transliterated",
                record_a_id=str(record_a.id),
                record_b_id=str(record_b.id),
                name_a_original=record_a.name,
                name_b_original=record_b.name,
                name_a_processed=name_a,
                name_b_processed=name_b,
                similarity=round(similarity, 3)
            )
            return True
    
    # ... rest of existing code ...
```

**Dependencies:**
```bash
# Add to backend/requirements.txt
unidecode==1.3.6
```

**Tests to add:**
```python
# backend/tests/test_merger.py

def test_transliterate_nepali_to_english(self, db_session):
    """Nepali names transliterate to Latin script."""
    pipeline = MergingPipeline(db_session)
    
    assert "kathmandu" in pipeline._transliterate_name("काठमाडौं")
    assert "hotel" in pipeline._transliterate_name("होटल")

def test_normalize_removes_prefixes_suffixes(self, db_session):
    """Name normalization removes common hotel prefixes/suffixes."""
    pipeline = MergingPipeline(db_session)
    
    assert pipeline._normalize_hotel_name("The Everest Hotel") == "everest"
    assert pipeline._normalize_hotel_name("Hotel Himalaya Pvt. Ltd.") == "himalaya"

def test_nepali_english_names_match(self, db_session):
    """Nepali and English names of same hotel match after transliteration."""
    make_source(db_session, 2, "booking_com")
    make_source(db_session, 30, "google_maps")
    job_id = make_job(db_session)
    
    # Google Maps: Nepali name
    r1 = make_result(
        db_session, job_id, 30,
        name="काठमाडौं बुटिक होटल", city="Kathmandu",
    )
    # Booking.com: English name
    r2 = make_result(
        db_session, job_id, 2,
        name="Kathmandu Boutique Hotel", city="Kathmandu",
    )
    
    pipeline = MergingPipeline(db_session)
    stats = pipeline.run(job_id)
    
    # Should merge via fuzzy matching (transliterated name match)
    assert stats["fuzzy_merged_groups"] >= 1
```

**Effort:** 1-2 hours  
**Expected Impact:** 0% → 20-40% merge rate  
**Risk:** LOW (no breaking changes)

---

## Expected Results

### Before Enhancement
```
"काठमाडौं बुटिक होटल" vs "Kathmandu Boutique Hotel"
→ 0% similarity ❌

"The Everest Hotel" vs "Everest Hotel Pvt. Ltd."
→ 65% similarity ❌ (below 80% threshold)
```

### After Enhancement
```
"काठमाडौं बुटिक होटल" → "kathmandu butik hotal"
"Kathmandu Boutique Hotel" → "kathmandu boutique hotel"
→ 85% similarity ✅

"The Everest Hotel" → "everest"
"Everest Hotel Pvt. Ltd." → "everest"
→ 100% similarity ✅
```

**Estimated merge rate improvement: 0% → 20-40%**

---

## Implementation Steps

1. **Install unidecode** (5 min)
   ```bash
   echo "unidecode==1.3.6" >> backend/requirements.txt
   docker-compose build backend
   ```

2. **Add methods to merger.py** (30 min)
   - `_transliterate_name()`
   - `_normalize_hotel_name()`
   - Update `_are_same_business()`

3. **Add tests** (30 min)
   - Transliteration tests
   - Normalization tests
   - Integration tests

4. **Run tests** (5 min)
   ```bash
   docker-compose run --rm -e PYTHONPATH=/app backend pytest tests/test_merger.py -v
   ```

5. **Re-run live test** (10 min)
   - Create new job with same config
   - Verify merge rate improvement

**Total time: 1.5-2 hours**

---

## Question for Supervisor

**Is there a more optimal solution than transliteration + normalization?**

Should we consider:
- Different similarity threshold (lower than 80%)?
- Larger coordinate radius (100m instead of 50m)?
- Token-based matching instead of full string similarity?
- Machine learning approach for name matching?
- Something else I'm missing?

Or should I proceed with the transliteration + normalization approach?
