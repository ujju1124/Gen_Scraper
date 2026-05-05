# Priority 4 - Hostelworld Selectors Implementation

**Goal:** Activate Hostelworld source with proper selectors  
**Estimated Time:** 2 hours  
**Status:** In Progress

---

## Step 1: Analyze Hostelworld Page Structure

### URL Pattern
```
https://www.hostelworld.com/hostels/asia/nepal/{city}/
Example: https://www.hostelworld.com/hostels/asia/nepal/kathmandu/
```

### Page Analysis (from rendered content)

**Hostel Card Structure:**
Each hostel listing contains:
- **Name:** "Kwabahal Boutique Hostel"
- **Rating:** "9.4 Superb (169)" - includes score, label, and review count
- **Distance:** "1.22km from city centre"
- **Description:** Short text about the hostel
- **Price:** "Privates From NPR1615.22" and "Dorms From NPR1094.53"
- **Link:** Detail page URL (e.g., `/hostels/p/320494/kwabahal-boutique-hostel/`)
- **Events:** "96 events" (some hostels)
- **Badges:** "Covid-19 safe", "Select Pill Hostel", etc.

**Pagination:**
- Page numbers at bottom: 1, 2, 3, 4
- URL pattern: `?page=2`, `?page=3`, etc.

---

## Step 2: Identify CSS Selectors

Based on the rendered content and typical Hostelworld structure, likely selectors are:

### Proposed Selectors (to be verified)

```sql
-- Card container (each hostel listing)
card_container: 'a[href*="/hostels/p/"]' or 'div[data-testid="property-card"]'

-- Hostel name
name: 'h3' or '[data-testid="property-name"]' or 'a[href*="/hostels/p/"] h3'

-- Rating (e.g., "9.4 Superb (169)")
rating: '[data-testid="rating"]' or 'span:contains("Superb")' parent

-- Distance from city centre
distance: 'span:contains("from city centre")' or '[data-testid="distance"]'

-- Price (dorm beds)
price_dorm: 'span:contains("Dorms From")' or '[data-testid="price-dorm"]'

-- Price (private rooms)
price_private: 'span:contains("Privates From")' or '[data-testid="price-private"]'

-- Description
description: 'p' or '[data-testid="property-description"]'

-- Detail page link
detail_link: 'a[href*="/hostels/p/"]'

-- Thumbnail image
thumbnail: 'img[alt]' or '[data-testid="property-image"]'

-- Pagination next button
pagination_next: 'a:contains("Next")' or '[data-testid="pagination-next"]' or 'a[href*="?page="]'
```

---

## Step 3: Implementation Strategy

Since Hostelworld is a JavaScript-heavy site (React/Next.js), we need to:

1. **Use Playwright with wait_until="networkidle"**
2. **Wait for dynamic content to load** (2-3 seconds)
3. **Handle CAPTCHA detection**
4. **Extract data from rendered DOM**

### Key Challenges

1. **Dynamic rendering:** Content loads via JavaScript
2. **Anti-scraping:** May have CAPTCHA or rate limiting
3. **Complex selectors:** Modern React apps use dynamic class names
4. **Pagination:** Need to detect "no more pages" condition

---

## Step 4: Next Actions

### Option A: Manual Selector Extraction (RECOMMENDED)
1. Visit https://www.hostelworld.com/hostels/asia/nepal/kathmandu/ in browser
2. Open DevTools (F12)
3. Inspect hostel card elements
4. Copy exact CSS selectors
5. Add to database via seed.py
6. Test with live scraper

### Option B: Automated Selector Discovery
1. Create a test script that visits the page
2. Try multiple selector patterns
3. Log which selectors return data
4. Choose the most reliable ones

---

## Decision Point

**Which approach should we use?**

I recommend **Option A** because:
- ✅ More reliable (we see exactly what we're selecting)
- ✅ Faster (no trial-and-error)
- ✅ Better understanding of page structure
- ✅ Can verify selectors work before coding

**However, I cannot open a browser directly right now** (Playwright browser was closed).

**Alternative:** I can implement the scraper with **best-guess selectors** based on the rendered content, then we test and adjust.

---

## Proposed Implementation (Best-Guess Selectors)

Based on the rendered content analysis, here are the most likely selectors:

```python
# Selectors to add to database
HOSTELWORLD_SELECTORS = {
    'card_container': 'a[href*="/hostels/p/"]',  # Each hostel link is a card
    'name': 'h3, h2',  # Hostel name in heading
    'rating_text': 'span',  # Contains "9.4 Superb (169)"
    'distance': 'span',  # Contains "km from city centre"
    'price_dorm': 'span',  # Contains "Dorms From"
    'price_private': 'span',  # Contains "Privates From"
    'description': 'p',  # Description text
    'detail_link': 'self',  # The card itself is the link
    'thumbnail': 'img',  # Image within card
    'pagination_next': 'a[href*="?page="]',  # Next page link
}
```

---

## Recommendation

**Let's proceed with implementation using best-guess selectors**, then:
1. Add selectors to database
2. Implement scraping logic
3. Run test job
4. Adjust selectors based on results
5. Iterate until working

This is faster than waiting for manual browser inspection.

**Proceed with implementation?**
