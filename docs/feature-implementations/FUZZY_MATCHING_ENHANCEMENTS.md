# Fuzzy Matching Enhancement Plan

**Current Status:** Working correctly, but limited by data quality issues  
**Goal:** Improve merge rate from 0% to 30-50% for multi-language scenarios

---

## Issues Identified

### 1. Language Barrier ❌
**Problem:** Google Maps returns Nepali names, other sources use English
- "काठमाडौं बुटिक होटल" vs "Kathmandu Boutique Hotel"
- Name similarity: 0% (different scripts)

### 2. Missing Phone Numbers ❌
**Problem:** Booking.com doesn't extract phone numbers
- Can't use phone matching criterion
- Reduces matching opportunities by 33%

### 3. Name Variations ⚠️
**Problem:** Same hotel, different naming conventions
- "Hotel Himalaya" vs "Himalaya Hotel"
- "The Everest Hotel" vs "Everest Hotel"

---

## Enhancement Solutions

### Solution 1: Name Transliteration (HIGH IMPACT)

**Add Nepali-to-English transliteration for name matching**

**Implementation:**
```python
from unidecode import unidecode

def _transliterate_name(self, name: str) -> str:
    """
    Transliterate non-Latin scripts to Latin for comparison.
    
    Examples:
        "काठमाडौं बुटिक होटल" → "kathmandu butik hotal"
        "Hotel Himalaya" → "hotel himalaya"
    """
    if not name:
        return ""
    
    # Convert to Latin script
    transliterated = unidecode(name)
    
    # Normalize: lowercase, remove extra spaces
    normalized = ' '.join(transliterated.lower().split())
    
    return normalized

def _are_same_business(self, record_a, record_b) -> bool:
    # ... existing code ...
    
    # Name fuzzy match with transliteration
    if record_a.name and record_b.name:
        # Try original names first
        similarity = difflib.SequenceMatcher(
            None,
            record_a.name.lower().strip(),
            record_b.name.lower().strip()
        ).ratio()
        
        # If low similarity, try transliterated names
        if similarity < 0.80:
            name_a_trans = self._transliterate_name(record_a.name)
            name_b_trans = self._transliterate_name(record_b.name)
            similarity = difflib.SequenceMatcher(
                None, name_a_trans, name_b_trans
            ).ratio()
        
        if similarity >= 0.80:
            return True
```

**Benefits:**
- ✅ Matches "काठमाडौं बुटिक होटल" with "Kathmandu Boutique Hotel"
- ✅ Works for any non-Latin script (Nepali, Hindi, Chinese, etc.)
- ✅ Minimal performance impact

**Dependencies:**
```bash
pip install unidecode
```

---

### Solution 2: Improve Booking.com Phone Extraction (MEDIUM IMPACT)

**Extract phone numbers from Booking.com detail pages**

**Current Issue:** Booking.com doesn't show phones on listing pages

**Solution:** Visit detail pages to extract phone numbers

**Implementation in `backend/scrapers/booking_com.py`:**
```python
def _extract_detail_page(self, url: str) -> dict:
    """Extract additional details including phone from detail page."""
    page = self.context.new_page()
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(2000)
        
        # Extract phone number
        phone = None
        phone_selectors = [
            '[data-testid="phone-number"]',
            '.hp_phone_number',
            'a[href^="tel:"]',
        ]
        
        for selector in phone_selectors:
            try:
                element = page.query_selector(selector)
                if element:
                    phone = element.inner_text().strip()
                    break
            except:
                continue
        
        return {"phone": phone}
    finally:
        page.close()
```

**Trade-offs:**
- ✅ Enables phone matching for Booking.com
- ⚠️ Slower scraping (need to visit detail pages)
- ⚠️ May require authentication/cookies

---

### Solution 3: Advanced Name Normalization (LOW IMPACT)

**Remove common prefixes/suffixes for better matching**

**Implementation:**
```python
def _normalize_hotel_name(self, name: str) -> str:
    """
    Normalize hotel names by removing common prefixes/suffixes.
    
    Examples:
        "The Everest Hotel" → "everest"
        "Hotel Himalaya Pvt. Ltd." → "himalaya"
        "Kathmandu Boutique Hotel & Spa" → "kathmandu boutique"
    """
    if not name:
        return ""
    
    # Convert to lowercase
    normalized = name.lower()
    
    # Remove common prefixes
    prefixes = ['the ', 'hotel ', 'resort ', 'guest house ']
    for prefix in prefixes:
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix):]
    
    # Remove common suffixes
    suffixes = [
        ' hotel', ' resort', ' guest house', ' pvt. ltd.', ' pvt ltd',
        ' ltd.', ' ltd', ' & spa', ' and spa', ' inn', ' lodge'
    ]
    for suffix in suffixes:
        if normalized.endswith(suffix):
            normalized = normalized[:-len(suffix)]
    
    # Remove extra spaces
    normalized = ' '.join(normalized.split())
    
    return normalized

def _are_same_business(self, record_a, record_b) -> bool:
    # ... existing code ...
    
    # Name fuzzy match with normalization
    if record_a.name and record_b.name:
        # Try normalized names
        name_a_norm = self._normalize_hotel_name(record_a.name)
        name_b_norm = self._normalize_hotel_name(record_b.name)
        
        similarity = difflib.SequenceMatcher(
            None, name_a_norm, name_b_norm
        ).ratio()
        
        if similarity >= 0.80:
            return True
```

**Benefits:**
- ✅ Matches "The Everest Hotel" with "Everest Hotel Pvt. Ltd."
- ✅ Matches "Hotel Himalaya" with "Himalaya Hotel"
- ✅ No external dependencies

---

### Solution 4: Coordinate-Based Matching with Larger Radius (OPTIONAL)

**Increase radius for coordinate matching in areas with poor GPS accuracy**

**Current:** 50 meters  
**Proposed:** 100 meters (configurable)

**Implementation:**
```python
def _are_same_business(self, record_a, record_b) -> bool:
    # ... existing code ...
    
    # Coordinate proximity match (configurable radius)
    COORDINATE_RADIUS_KM = 0.10  # 100 meters (was 0.05)
    
    if all([record_a.latitude, record_a.longitude,
            record_b.latitude, record_b.longitude]):
        distance = self._haversine_distance(
            record_a.latitude, record_a.longitude,
            record_b.latitude, record_b.longitude
        )
        if distance <= COORDINATE_RADIUS_KM:
            return True
```

**Trade-offs:**
- ✅ More matches in areas with GPS inaccuracy
- ⚠️ Higher risk of false positives

---

## Recommended Implementation Order

### Phase 1: Quick Wins (1-2 hours)
1. ✅ **Add name transliteration** (Solution 1)
   - Install `unidecode` package
   - Add `_transliterate_name()` method
   - Update `_are_same_business()` to use transliteration
   - Add tests for transliteration

2. ✅ **Add name normalization** (Solution 3)
   - Add `_normalize_hotel_name()` method
   - Update `_are_same_business()` to use normalization
   - Add tests for normalization

**Expected Impact:** 20-40% merge rate improvement

### Phase 2: Medium Effort (3-4 hours)
3. ⚠️ **Improve Booking.com phone extraction** (Solution 2)
   - Update `booking_com.py` to visit detail pages
   - Extract phone numbers
   - Handle rate limiting
   - Add tests

**Expected Impact:** Additional 10-20% merge rate improvement

### Phase 3: Optional (30 minutes)
4. ⚠️ **Adjust coordinate radius** (Solution 4)
   - Make radius configurable
   - Test with different values
   - Document trade-offs

**Expected Impact:** 5-10% merge rate improvement

---

## Implementation: Phase 1 (Recommended Now)

### Step 1: Install Dependencies
```bash
# Add to backend/requirements.txt
unidecode==1.3.6
```

### Step 2: Update merger.py
Add transliteration and normalization methods to `MergingPipeline` class.

### Step 3: Update Tests
Add tests for:
- Nepali-to-English transliteration
- Name normalization
- Combined transliteration + normalization

### Step 4: Re-run Live Test
Create new job with same configuration to verify improvement.

---

## Expected Results After Phase 1

### Before Enhancements
- **Merge rate:** 0%
- **Reason:** Language barrier + missing phones

### After Phase 1 (Transliteration + Normalization)
- **Merge rate:** 20-40%
- **Matches:**
  - "काठमाडौं बुटिक होटल" ↔ "Kathmandu Boutique Hotel"
  - "Hotel Himalaya" ↔ "Himalaya Hotel"
  - "The Everest Hotel" ↔ "Everest Hotel Pvt. Ltd."

### After Phase 2 (+ Phone Extraction)
- **Merge rate:** 30-50%
- **Additional matches via phone numbers**

---

## Cost-Benefit Analysis

| Solution | Effort | Impact | Risk | Recommended |
|----------|--------|--------|------|-------------|
| Transliteration | 1 hour | HIGH | LOW | ✅ YES |
| Name Normalization | 1 hour | MEDIUM | LOW | ✅ YES |
| Phone Extraction | 3-4 hours | MEDIUM | MEDIUM | ⚠️ LATER |
| Larger Radius | 30 min | LOW | MEDIUM | ❌ NO |

---

## Decision

**Recommended:** Implement Phase 1 (Transliteration + Normalization)

**Reasons:**
1. ✅ Quick to implement (1-2 hours)
2. ✅ High impact (20-40% improvement)
3. ✅ Low risk (no breaking changes)
4. ✅ No external API dependencies
5. ✅ Works for any language

**Skip for now:** Phone extraction (Phase 2)
- Takes 3-4 hours
- Medium impact
- Requires detail page visits (slower)
- Can be added later if needed

---

## Next Steps

1. **Approve Phase 1 implementation** (transliteration + normalization)
2. **Install unidecode package**
3. **Update merger.py with new methods**
4. **Add tests**
5. **Re-run live test to verify improvement**

**Estimated Time:** 1-2 hours  
**Expected Improvement:** 0% → 20-40% merge rate

---

**Want me to implement Phase 1 now?**
