# Hostelworld Migration Plan

**Date**: 2026-05-12  
**Status**: READY TO MIGRATE  
**Estimated Time**: 2-3 hours

---

## Current Implementation Analysis

### Extraction Method
The current Hostelworld scraper uses **text parsing** instead of selectors:
- Gets entire card text with `card.inner_text()`
- Uses regex to extract data from text
- No specific element selectors for fields

### Current Extraction Logic

```python
# Name: First line of card text
lines = [line.strip() for line in card_text.split('\n') if line.strip()]
result['name'] = lines[0]

# Rating: Regex pattern "9.4 Superb (169)"
rating_match = re.search(r'(\d+\.?\d*)\s+(Superb|Excellent|...)\s+\((\d+)\)', card_text)

# Distance: Regex pattern "1.22km from city centre"
distance_match = re.search(r'([\d.]+)km from city centre', card_text)

# Price: Regex pattern "Dorms From NPR1094.53"
dorm_match = re.search(r'Dorms From\s+NPR\s*([\d,]+\.?\d*)', card_text)
```

### Challenges

1. **Text-based extraction** - Not compatible with healing system
2. **No element selectors** - Healing needs specific selectors
3. **Regex parsing** - Fragile, breaks when text format changes
4. **No selector database** - Need to add selectors first

---

## Migration Strategy

### Option 1: Full Healing Migration (Recommended)

**Approach**: Replace text parsing with element-based extraction using healing system

**Steps**:
1. Inspect Hostelworld website to find element selectors
2. Add selectors to database
3. Replace text parsing with `_extract_field_with_healing()`
4. Add field hints
5. Test

**Pros**:
- ✅ Full healing capability
- ✅ More robust than regex
- ✅ Consistent with other scrapers
- ✅ Future-proof

**Cons**:
- ❌ Requires website inspection
- ❌ More work upfront
- ❌ May hit anti-bot (like Agoda)

### Option 2: Hybrid Approach

**Approach**: Keep text parsing but add healing for critical fields

**Steps**:
1. Keep regex for most fields
2. Add healing only for name and price
3. Fallback to regex if healing fails

**Pros**:
- ✅ Faster implementation
- ✅ Maintains current functionality
- ✅ Adds healing for critical fields

**Cons**:
- ❌ Not fully migrated
- ❌ Still relies on fragile regex
- ❌ Inconsistent with other scrapers

### Option 3: Skip for Now

**Approach**: Mark as "needs investigation" and move to easier scrapers

**Pros**:
- ✅ Focus on scrapers with existing selectors
- ✅ Come back when we have more examples

**Cons**:
- ❌ Delays migration
- ❌ Hostelworld remains fragile

---

## Recommended Approach: Option 1 (Full Migration)

### Phase 1: Website Inspection

**Goal**: Find actual element selectors on Hostelworld

**Tasks**:
1. Navigate to Hostelworld search page
2. Inspect card structure
3. Identify selectors for each field
4. Document selector patterns

**URL to inspect**:
```
https://www.hostelworld.com/hostels/asia/nepal/kathmandu/
```

**Fields to find selectors for**:
- Card container (list of hostels)
- Name
- Rating
- Review count
- Price (dorm)
- Price (private)
- Distance
- Thumbnail image
- Description

### Phase 2: Database Setup

**Add selectors to database**:

```sql
-- Get Hostelworld source ID
SELECT id FROM sources WHERE name = 'hostelworld';

-- Add selectors (replace with actual selectors from inspection)
INSERT INTO scraper_selectors (source_id, field_name, selector, selector_type, is_active)
VALUES
    (6, 'card_container', '[data-testid="property-card"], .hostel-card', 'css', true),
    (6, 'name', 'h3.hostel-name, [data-testid="hostel-name"]', 'css', true),
    (6, 'rating', '.rating-score, [data-testid="rating"]', 'css', true),
    (6, 'review_count', '.review-count, [data-testid="reviews"]', 'css', true),
    (6, 'price_dorm', '.price-dorm, [data-testid="dorm-price"]', 'css', true),
    (6, 'price_private', '.price-private, [data-testid="private-price"]', 'css', true),
    (6, 'distance', '.distance, [data-testid="distance"]', 'css', true),
    (6, 'thumbnail', 'img.hostel-image, [data-testid="image"]', 'css', true),
    (6, 'description', '.description, [data-testid="description"]', 'css', true);

-- Add field hints (real values from website)
UPDATE sources
SET field_hints = '{
    "name": "Kathmandu Madhuban Guest House",
    "rating": "9.4",
    "review_count": "169",
    "price_dorm": "NPR 1094.53",
    "price_private": "NPR 1615.22",
    "distance": "1.22km from city centre"
}'::jsonb
WHERE id = 6;

-- Set heal mode to AUTO
UPDATE sources SET heal_mode = 'AUTO' WHERE id = 6;
```

### Phase 3: Code Migration

**Replace text parsing with healing**:

```python
async def _extract_hostel_data(self, card, page, source, db, location) -> Optional[dict]:
    """Extract hostel data from card using healing system."""
    
    # Extract name with healing
    name = await self._extract_field_with_healing(
        card=card,
        page=page,
        source=source,
        db=db,
        field_name='name'
    )
    
    if not name:
        return None  # Name is critical
    
    # Extract rating with healing
    rating_text = await self._extract_field_with_healing(
        card=card,
        page=page,
        source=source,
        db=db,
        field_name='rating'
    )
    
    rating_overall = None
    if rating_text:
        rating_match = re.search(r'(\d+\.?\d*)', rating_text)
        if rating_match:
            rating_overall = float(rating_match.group(1))
    
    # Extract review count with healing
    review_text = await self._extract_field_with_healing(
        card=card,
        page=page,
        source=source,
        db=db,
        field_name='review_count'
    )
    
    review_count = None
    if review_text:
        review_match = re.search(r'(\d+)', review_text)
        if review_match:
            review_count = int(review_match.group(1))
    
    # Extract dorm price with healing
    price_dorm_text = await self._extract_field_with_healing(
        card=card,
        page=page,
        source=source,
        db=db,
        field_name='price_dorm'
    )
    
    price_min = None
    if price_dorm_text:
        price_match = re.search(r'([\d,]+\.?\d*)', price_dorm_text)
        if price_match:
            price_min = float(price_match.group(1).replace(',', ''))
    
    # Extract private price with healing
    price_private_text = await self._extract_field_with_healing(
        card=card,
        page=page,
        source=source,
        db=db,
        field_name='price_private'
    )
    
    price_max = None
    if price_private_text:
        price_match = re.search(r'([\d,]+\.?\d*)', price_private_text)
        if price_match:
            price_max = float(price_match.group(1).replace(',', ''))
    
    # Extract distance with healing
    distance_text = await self._extract_field_with_healing(
        card=card,
        page=page,
        source=source,
        db=db,
        field_name='distance'
    )
    
    distance_from_centre = None
    if distance_text:
        distance_match = re.search(r'([\d.]+)', distance_text)
        if distance_match:
            distance_from_centre = float(distance_match.group(1))
    
    return {
        "name": name,
        "rating_overall": rating_overall,
        "review_count": review_count,
        "price_min": price_min,
        "price_max": price_max,
        "distance_from_centre": distance_from_centre,
        "city": location,
        "country": "Nepal",
        "property_type": "Hostel",
        "currency": "NPR"
    }
```

### Phase 4: Testing

**Test plan**:
1. Normal scrape test
2. Healing test (break selector)
3. Skip-reload verification
4. Restore selector

---

## Alternative: Simpler Scrapers First

**Recommendation**: If Hostelworld inspection is complex, consider migrating simpler scrapers first:

1. **DirectoryOfNepal** - Already active, likely simpler structure
2. **NepalYP** - Directory listing, may be easier
3. **OYO Rooms** - Similar to Booking.com/Agoda

**Rationale**:
- Build confidence with easier migrations
- Establish patterns for complex scrapers
- Come back to Hostelworld with more experience

---

## Decision Point

### Questions to Answer:

1. **Can we access Hostelworld website?**
   - If blocked by anti-bot: Skip for now
   - If accessible: Proceed with migration

2. **How complex is the card structure?**
   - If simple: Full migration (2-3 hours)
   - If complex: Consider hybrid or skip

3. **Is Hostelworld data critical?**
   - If yes: Invest time in full migration
   - If no: Focus on other sources

---

## Next Steps

### Option A: Proceed with Hostelworld
1. Inspect website for selectors
2. Add selectors to database
3. Migrate code
4. Test

### Option B: Skip to Simpler Scraper
1. Check DirectoryOfNepal structure
2. Check NepalYP structure
3. Migrate whichever is simpler
4. Come back to Hostelworld later

---

## Recommendation

**Skip Hostelworld for now and focus on DirectoryOfNepal or NepalYP.**

**Reasons**:
1. Hostelworld uses text parsing (requires full rewrite)
2. May have anti-bot like Agoda
3. Other scrapers likely easier to migrate
4. Build momentum with quick wins

**Timeline**:
- DirectoryOfNepal/NepalYP: 1-2 hours each
- Hostelworld: 3-4 hours (after inspection)

**Priority Order**:
1. DirectoryOfNepal (active, likely simple)
2. NepalYP (multiple categories, establish pattern)
3. OYO Rooms (similar to Booking.com)
4. eSewa Hotels (similar to Booking.com)
5. Hostelworld (complex, needs inspection)

---

**Status**: PLAN COMPLETE  
**Decision**: Move to DirectoryOfNepal or NepalYP  
**Next Action**: Inspect DirectoryOfNepal scraper

