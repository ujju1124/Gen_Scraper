# Priority 4 - Hostelworld Selector Issue

**Date:** May 4, 2026  
**Status:** ⚠️ Selector Issue Identified  
**Job ID:** bff16122-0941-4ce2-9dfc-aa6bdbd023ee

---

## Issue Summary

Hostelworld scraper is running but **extracting 0 results** despite finding 49 hostel cards.

### Root Cause

The `name` selector (`h3, h2`) is not finding hostel names within the card structure.

**Evidence from logs:**
```
[warning] scraper.no_name_found card_index=45 card_text_preview=Thamel Hotel & Spa
[warning] scraper.no_name_found card_index=46 card_text_preview=Khangsar Home Hostel
[warning] scraper.no_name_found card_index=47 card_text_preview=My Garden House
```

The scraper CAN see the names in the card text, but the selector isn't matching them.

---

## Problem Analysis

### Current Implementation
```python
# Extract name (first heading in card)
if 'name' in self.selectors:
    name_elem = await card.query_selector(self.selectors['name'].selector)
    if name_elem:
        result['name'] = (await name_elem.inner_text()).strip()
```

### Hostelworld Structure
The card is an `<a>` link element, and the name appears to be:
- NOT in an `<h3>` or `<h2>` tag
- Possibly in a `<div>`, `<span>`, or as direct text
- Visible in `card.inner_text()` but not via the heading selector

---

## Solution Options

### Option 1: Parse Name from Card Text (QUICK FIX)
Extract the first line of card text as the name:

```python
# Get card text
card_text = await card.inner_text()

# Extract name (first non-empty line)
lines = [line.strip() for line in card_text.split('\n') if line.strip()]
if lines:
    result['name'] = lines[0]
```

**Pros:** Works immediately, no selector changes needed  
**Cons:** Less precise, might grab wrong text

### Option 2: Inspect Actual HTML Structure (PROPER FIX)
1. Visit https://www.hostelworld.com/hostels/asia/nepal/kathmandu/
2. Inspect a hostel card in DevTools
3. Find the exact selector for the name element
4. Update database with correct selector

**Pros:** Precise, reliable  
**Cons:** Requires manual inspection

### Option 3: Try Multiple Selectors
Update code to try multiple possible selectors:

```python
name_selectors = ['h3', 'h2', 'h4', '.property-name', '[data-testid="property-name"]', 'div']
for selector in name_selectors:
    name_elem = await card.query_selector(selector)
    if name_elem:
        result['name'] = (await name_elem.inner_text()).strip()
        break
```

**Pros:** Flexible, handles structure changes  
**Cons:** Slower, might match wrong elements

---

## Recommended Fix

**Implement Option 1 immediately** (parse from card text) to get Hostelworld working, then **do Option 2** (proper selectors) for long-term reliability.

### Implementation Steps

1. **Update `hostelworld.py`** - Change name extraction logic:
```python
# Get inner text of the entire card for parsing
card_text = await card.inner_text()

# Extract name (first substantial line, before rating)
lines = [line.strip() for line in card_text.split('\n') if line.strip()]
if lines:
    # First line is usually the hostel name
    result['name'] = lines[0]
```

2. **Test with new job** - Create another test job

3. **Verify results** - Should extract 10-25 hostels

---

## Current Job Status

- **Job ID:** bff16122-0941-4ce2-9dfc-aa6bdbd023ee
- **Status:** RUNNING (Google Maps still scraping)
- **Hostelworld Results:** 0 (selector issue)
- **Google Maps Results:** ~28 (working)

---

## Next Steps

1. Wait for current job to complete
2. Implement Option 1 fix in `hostelworld.py`
3. Create new test job
4. Verify Hostelworld extracts names correctly
5. (Optional) Do proper selector inspection for Option 2

---

**Estimated Fix Time:** 15 minutes
