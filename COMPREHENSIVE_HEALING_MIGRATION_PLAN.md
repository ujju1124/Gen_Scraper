# Comprehensive Healing Migration Plan - All Sources

**Date**: 2026-05-12  
**Goal**: Migrate ALL applicable scrapers to self-healing system  
**Priority**: HIGH - This is the main selling point

---

## Executive Summary

**Total Sources**: 32
**Applicable for Healing**: 8 Playwright-based scrapers
**Already Migrated**: 2 (Booking.com, Agoda)
**To Migrate**: 6 scrapers
**Not Applicable**: 24 sources (httpx-based or NepalYP variants using same scraper)

---

## Scraper Classification

### ✅ Already Migrated (2)
1. **Booking.com** - Fully tested and verified
2. **Agoda** - Fully migrated (blocked by anti-bot)

### 🔧 Need Migration (6 Playwright scrapers)
3. **OYO Rooms** - Similar to Agoda, uses locators
4. **eSewa Hotels** - Uses query_selector_all
5. **NepalYP** (base) - Directory listing, uses query_selector_all
6. **Foodmandu** - Restaurant scraper, uses query_selector
7. **Hostelworld** - Uses text parsing (complex)
8. **Google Maps** - Universal source (complex)

### ➖ Not Applicable (24 sources)
- **DirectoryOfNepal** (3 variants) - Uses httpx, not Playwright
- **NepalYP** (21 variants) - All use same base NepalYPScraper class

---

## Migration Strategy

### Phase 1: Simple Migrations (OYO, eSewa, NepalYP, Foodmandu)
**Estimated Time**: 4-6 hours total
**Approach**: Add selectors, modify extraction, test

### Phase 2: Complex Migrations (Hostelworld, Google Maps)
**Estimated Time**: 6-8 hours total
**Approach**: Full rewrite with healing

---

## Detailed Migration Plans

### 1. OYO Rooms Migration

**Current State**:
- Uses Playwright locator API
- Extracts: name, address, price, rating
- Multiple selector fallbacks already

**Migration Steps**:
1. Add selectors to database
2. Replace locator extraction with `_extract_field_with_healing()`
3. Add field hints
4. Test

**Selectors Needed**:
```sql
-- OYO Rooms selectors
INSERT INTO scraper_selectors (source_id, field_name, selector, selector_type, is_active)
VALUES
    (3, 'name', 'h3, [data-testid="hotel-name"], .hotelName, [class*="hotelName"]', 'css', true),
    (3, 'address', '[title], .address, [class*="address"]', 'css', true),
    (3, 'price', '[data-testid="price"], [class*="price"], [class*="Price"]', 'css', true),
    (3, 'rating', '[class*="rating"], [class*="Rating"]', 'css', true);
```

**Field Hints**:
```json
{
  "name": "OYO Hotel Example",
  "address": "Thamel, Kathmandu",
  "price": "NPR 2500",
  "rating": "4.2"
}
```

---

### 2. eSewa Hotels Migration

**Current State**:
- Uses query_selector_all for hotel links
- Extracts: name, price, rating
- Simple structure

**Migration Steps**:
1. Add selectors to database
2. Modify extraction to use healing
3. Add field hints
4. Test

**Selectors Needed**:
```sql
-- eSewa Hotels selectors
INSERT INTO scraper_selectors (source_id, field_name, selector, selector_type, is_active)
VALUES
    (4, 'name', 'h5, h4, h3, .hotel-name, .title, [class*="hotelName"]', 'css', true),
    (4, 'price', '.price, .hotel-price, span:has-text("NPR"), [class*="price"]', 'css', true),
    (4, 'rating', '.rating, [class*="rating"], [class*="Rating"]', 'css', true);
```

**Field Hints**:
```json
{
  "name": "Hotel Example Kathmandu",
  "price": "NPR 3500",
  "rating": "4.5"
}
```

---

### 3. NepalYP Migration

**Current State**:
- Uses query_selector_all for company links
- Extracts: name, address, phone, email
- Directory listing format

**Migration Steps**:
1. Add selectors to database
2. Modify extraction to use healing
3. Add field hints
4. Test

**Selectors Needed**:
```sql
-- NepalYP selectors (applies to all 22 NepalYP sources)
INSERT INTO scraper_selectors (source_id, field_name, selector, selector_type, is_active)
VALUES
    (5, 'name', 'h3, h4, .company-name, .title, [class*="name"]', 'css', true),
    (5, 'address', '.address, .location, [class*="address"], [class*="location"]', 'css', true),
    (5, 'phone', 'a[href^="tel:"], .phone, [class*="phone"]', 'css', true),
    (5, 'email', 'a[href^="mailto:"], .email, [class*="email"]', 'css', true);
```

**Field Hints**:
```json
{
  "name": "Example Business Name",
  "address": "Thamel, Kathmandu",
  "phone": "+977-1-234567",
  "email": "info@example.com"
}
```

---

### 4. Foodmandu Migration

**Current State**:
- Uses query_selector for restaurant cards
- Extracts: name, address, cuisine, thumbnail
- Angular SPA with dynamic content

**Migration Steps**:
1. Add selectors to database
2. Modify extraction to use healing
3. Add field hints
4. Test

**Selectors Needed**:
```sql
-- Foodmandu selectors
INSERT INTO scraper_selectors (source_id, field_name, selector, selector_type, is_active)
VALUES
    (8, 'name', 'div.title20 a', 'css', true),
    (8, 'address', 'div.subtitle > div:first-child span:nth-child(2)', 'css', true),
    (8, 'cuisine', 'div.subtitle > div:nth-child(2) span:nth-child(2)', 'css', true),
    (8, 'thumbnail', 'div.listing__photo img', 'css', true);
```

**Field Hints**:
```json
{
  "name": "Restaurant Example",
  "address": "Thamel, Kathmandu",
  "cuisine": "Nepali | Indian | Chinese"
}
```

---

### 5. Hostelworld Migration (Complex)

**Current State**:
- Uses text parsing with regex
- No element selectors
- Needs full rewrite

**Migration Steps**:
1. Inspect website for actual selectors
2. Add selectors to database
3. Completely rewrite extraction logic
4. Add field hints
5. Test

**Estimated Time**: 3-4 hours

---

### 6. Google Maps Migration (Complex)

**Current State**:
- Already has 10 selectors in database
- Uses hardcoded selectors
- Complex extraction logic

**Migration Steps**:
1. Modify extraction to use healing
2. Add field hints
3. Test

**Estimated Time**: 2-3 hours

---

## Implementation Order

### Priority 1: Quick Wins (4-6 hours)
1. OYO Rooms (1 hour)
2. eSewa Hotels (1 hour)
3. NepalYP (1.5 hours)
4. Foodmandu (1.5 hours)

### Priority 2: Complex (6-8 hours)
5. Google Maps (2-3 hours)
6. Hostelworld (3-4 hours)

---

## Success Criteria

### Per Scraper
- [ ] Selectors added to database
- [ ] Field hints configured
- [ ] Heal mode set to AUTO
- [ ] Code uses `_extract_field_with_healing()`
- [ ] Normal scrape tested
- [ ] Healing tested (if accessible)
- [ ] Documentation updated

### Overall
- [ ] 8/8 Playwright scrapers migrated
- [ ] All use consistent healing pattern
- [ ] Graceful degradation verified
- [ ] Skip-reload working for all

---

## Risk Mitigation

### Anti-Bot Detection
**Risk**: Some scrapers may be blocked
**Mitigation**: Mark as "healing-ready" and continue

### Complex Rewrites
**Risk**: Hostelworld needs full rewrite
**Mitigation**: Do last, after building confidence

### Testing Limitations
**Risk**: Cannot test healing if blocked
**Mitigation**: Verify code correctness, test when accessible

---

## Next Steps

1. Start with OYO Rooms (simplest)
2. Move to eSewa Hotels
3. Migrate NepalYP
4. Migrate Foodmandu
5. Tackle Google Maps
6. Finally Hostelworld

---

**Total Estimated Time**: 10-14 hours
**Expected Completion**: 2 days
**Confidence**: HIGH (for simple migrations)

