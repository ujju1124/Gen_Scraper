# Async Fixes Summary - BookingComScraper & BaseScraper

## Overview
Fixed all Playwright/Camoufox calls to be async with proper `await` keywords. Camoufox uses Playwright's async API, so all page and element interactions must be awaited.

---

## Changes Applied

### 1. ✅ Made _scrape() Async

**BookingComScraper (`backend/scrapers/booking_com.py`):**
```python
# BEFORE
def _scrape(self, page, source, db, location) -> list[dict]:

# AFTER
async def _scrape(self, page, source, db, location) -> list[dict]:
```

**BaseScraper (`backend/scrapers/base_scraper.py`):**
```python
# BEFORE
@abstractmethod
def _scrape(self, page, source, db, location) -> list[dict]:

# AFTER
@abstractmethod
async def _scrape(self, page, source, db, location) -> list[dict]:
```

**BaseScraper.run() call:**
```python
# BEFORE
results = self._scrape(self.page, source, db, location)

# AFTER
results = await self._scrape(self.page, source, db, location)
```

---

### 2. ✅ Made _extract_hotel_data() Async

```python
# BEFORE
def _extract_hotel_data(self, card, source_id: int) -> Optional[dict]:

# AFTER
async def _extract_hotel_data(self, card, source_id: int) -> Optional[dict]:
```

---

### 3. ✅ Added await to All Page Calls

**In _scrape() method:**
```python
# BEFORE
page.goto(search_url, ...)
page.wait_for_selector(...)
html = page.content()
property_cards = page.query_selector_all(...)

# AFTER
await page.goto(search_url, ...)
await page.wait_for_selector(...)
html = await page.content()
property_cards = await page.query_selector_all(...)
```

---

### 4. ✅ Added await to All Element Calls

**In _extract_hotel_data() method:**
```python
# BEFORE
name_elem = card.query_selector('[data-testid="title"]')
if name_elem:
    data["name"] = name_elem.text_content().strip()

# AFTER
name_elem = await card.query_selector('[data-testid="title"]')
if name_elem:
    data["name"] = (await name_elem.text_content()).strip()
```

**All element operations updated:**
```python
# BEFORE
rating_elem = card.query_selector(...)
rating_text = rating_elem.text_content()
price_elem = card.query_selector(...)
price_text = price_elem.text_content()
address_elem = card.query_selector(...)
thumbnail_elem = card.query_selector(...)
img = thumbnail_elem.query_selector('img')
src = img.get_attribute('src')
link_elem = card.query_selector(...)
href = link_elem.get_attribute('href')

# AFTER
rating_elem = await card.query_selector(...)
rating_text = await rating_elem.text_content()
price_elem = await card.query_selector(...)
price_text = await price_elem.text_content()
address_elem = await card.query_selector(...)
thumbnail_elem = await card.query_selector(...)
img = await thumbnail_elem.query_selector('img')
src = await img.get_attribute('src')
link_elem = await card.query_selector(...)
href = await link_elem.get_attribute('href')
```

---

### 5. ✅ Made _detect_captcha() Async

**BaseScraper (`backend/scrapers/base_scraper.py`):**
```python
# BEFORE
def _detect_captcha(self) -> bool:
    if not self.page:
        return False
    title = self.page.title().lower()
    iframes = self.page.query_selector_all('iframe')
    for iframe in iframes:
        src = iframe.get_attribute('src')
    html = self.page.content()

# AFTER
async def _detect_captcha(self, page) -> bool:
    if not page:
        return False
    title = (await page.title()).lower()
    iframes = await page.query_selector_all('iframe')
    for iframe in iframes:
        src = await iframe.get_attribute('src')
    html = await page.content()
```

**BookingComScraper call:**
```python
# BEFORE
if self._detect_captcha():

# AFTER
if await self._detect_captcha(page):
```

---

### 6. ✅ Updated _extract_hotel_data() Call

**In _scrape() method:**
```python
# BEFORE
hotel_data = self._extract_hotel_data(card, source.id)

# AFTER
hotel_data = await self._extract_hotel_data(card, source.id)
```

---

## Complete List of Async Operations

### Page-Level Operations (all require await)
- ✅ `await page.goto(...)`
- ✅ `await page.wait_for_selector(...)`
- ✅ `await page.content()`
- ✅ `await page.query_selector_all(...)`
- ✅ `await page.title()`

### Element-Level Operations (all require await)
- ✅ `await card.query_selector(...)`
- ✅ `await element.text_content()`
- ✅ `await element.get_attribute(...)`
- ✅ `await element.query_selector(...)`

### Method Calls (all require await)
- ✅ `await self._scrape(...)`
- ✅ `await self._extract_hotel_data(...)`
- ✅ `await self._detect_captcha(...)`

---

## Why This Was Necessary

### Playwright/Camoufox Async API
Camoufox is built on Playwright, which uses an **async API** for all browser operations:

1. **Network Operations**: `page.goto()` waits for network requests
2. **DOM Queries**: `query_selector()` waits for elements to be available
3. **Content Extraction**: `text_content()` and `get_attribute()` are async
4. **Page State**: `title()` and `content()` are async

### Without await
```python
# ❌ WRONG - Returns a coroutine object, not the actual value
title = page.title()  # <coroutine object>
print(title)  # <coroutine object Page.title at 0x...>
```

### With await
```python
# ✅ CORRECT - Returns the actual title string
title = await page.title()  # "Booking.com: Hotels"
print(title)  # "Booking.com: Hotels"
```

---

## Files Modified

1. **`backend/scrapers/booking_com.py`**
   - Made `_scrape()` async
   - Made `_extract_hotel_data()` async
   - Added `await` to all page operations
   - Added `await` to all element operations
   - Added `await` to `_detect_captcha()` call
   - Added `await` to `_extract_hotel_data()` call

2. **`backend/scrapers/base_scraper.py`**
   - Made `_scrape()` abstract method async
   - Added `await` to `_scrape()` call in `run()`
   - Made `_detect_captcha()` async
   - Added `await` to all page operations in `_detect_captcha()`

---

## Testing Checklist

### Verify Async Operations
```python
# All these should work without errors:
async def test_scrape():
    scraper = BookingComScraper()
    results = await scraper._scrape(page, source, db, "Kathmandu")
    assert isinstance(results, list)

async def test_extract_hotel_data():
    scraper = BookingComScraper()
    data = await scraper._extract_hotel_data(card, source_id=1)
    assert data is not None
    assert "name" in data

async def test_detect_captcha():
    scraper = BookingComScraper()
    has_captcha = await scraper._detect_captcha(page)
    assert isinstance(has_captcha, bool)
```

### Common Async Errors to Watch For
```python
# ❌ RuntimeWarning: coroutine was never awaited
result = page.goto(...)  # Missing await

# ❌ TypeError: object NoneType can't be used in 'await' expression
await None  # Trying to await a non-coroutine

# ❌ AttributeError: 'coroutine' object has no attribute 'strip'
text = page.title().strip()  # Missing await before .strip()
```

---

## Summary

✅ **All async operations fixed**  
✅ **Methods properly declared as async**  
✅ **All await keywords added**  
✅ **Consistent async pattern throughout**  
✅ **Ready for Task 9**  

---

**Fixes Applied:** 2024-04-26  
**Files Modified:** 2 files (`booking_com.py`, `base_scraper.py`)  
**Status:** ✅ Complete - All async operations properly awaited
