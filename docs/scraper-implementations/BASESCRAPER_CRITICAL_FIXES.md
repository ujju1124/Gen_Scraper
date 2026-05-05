# BaseScraper Critical Fixes Summary

## Overview
Fixed critical bugs in BaseScraper to properly use AsyncCamoufox async context manager, remove instance variables, and implement auto-disable logic.

---

## Critical Fixes Applied

### 1. ✅ Made run() Async with AsyncCamoufox Context Manager

**Issue:** Using sync Camoufox API and storing browser/page as instance variables caused resource leaks.

**Fix:**
```python
# BEFORE
from camoufox.sync_api import Camoufox

def run(self, source, db, location):
    self.browser = Camoufox(...)
    self.page = self.browser.new_page()
    try:
        results = self._scrape(...)
    finally:
        if self.page:
            self.page.close()
        if self.browser:
            self.browser.close()

# AFTER
from camoufox.async_api import AsyncCamoufox

async def run(self, source, db, location):
    async with AsyncCamoufox(
        headless=True,
        os="windows",
        geoip=True
    ) as browser:
        context = await browser.new_context(
            viewport={"width": 1366, "height": 768},
            locale="en-US"
        )
        page = await context.new_page()
        
        try:
            await self._apply_anti_bot_measures(page)
            results = await self._scrape(page, source, db, location)
            await self._check_html_hash(page, source, db)
            return results
        except Exception as e:
            await self._handle_failure(page, source, db, e)
            return []
        finally:
            await page.close()
            await context.close()
```

**Benefits:**
- ✅ Automatic browser cleanup via context manager
- ✅ No resource leaks
- ✅ Proper async/await pattern
- ✅ Context and page properly closed in finally block

---

### 2. ✅ Removed Instance Variables (self.browser, self.page)

**Issue:** Storing browser and page as instance variables caused:
- Resource leaks if cleanup failed
- Confusion about which page to use
- Thread safety issues

**Fix:**
```python
# BEFORE
def __init__(self):
    self.source_name = None
    self.selectors = {}
    self.browser = None  # ❌ Removed
    self.page = None     # ❌ Removed

# AFTER
def __init__(self):
    self.source_name = None
    self.selectors = {}
    # No browser or page instance variables
```

**All methods now receive page as parameter:**
```python
# BEFORE
def _apply_anti_bot_measures(self):
    if not self.page:
        return
    self.page.add_init_script(...)

# AFTER
async def _apply_anti_bot_measures(self, page):
    if not page:
        return
    await page.add_init_script(...)
```

---

### 3. ✅ Made _apply_anti_bot_measures() Async

**Issue:** Method was sync but called async page methods.

**Fix:**
```python
# BEFORE
def _apply_anti_bot_measures(self):
    self.page.add_init_script(...)
    self.page.set_extra_http_headers(...)
    self.page.set_viewport_size(...)
    self.page.wait_for_timeout(...)

# AFTER
async def _apply_anti_bot_measures(self, page):
    await page.add_init_script(...)
    await page.set_extra_http_headers(...)
    await page.wait_for_timeout(...)
```

**Note:** Removed viewport and locale setting from this method since they're now set in `browser.new_context()`.

---

### 4. ✅ Made _handle_failure() Async

**Issue:** Method called `page.content()` without await.

**Fix:**
```python
# BEFORE
def _handle_failure(self, source, db, exception):
    if self.page:
        html = self.page.content()  # ❌ Missing await

# AFTER
async def _handle_failure(self, page, source, db, exception):
    if page:
        html = await page.content()  # ✅ Properly awaited
```

---

### 5. ✅ Added Auto-Disable Logic

**Issue:** Sources were not automatically disabled after 3 consecutive failures.

**Fix:**
```python
# In _handle_failure() after incrementing counter:
source.consecutive_failure_count += 1

logger.info(
    "scraper.failure_count_incremented",
    source_id=source.id,
    consecutive_failures=source.consecutive_failure_count
)

# Auto-disable source after 3 consecutive failures
if source.consecutive_failure_count >= 3:
    source.is_active = False
    logger.warning(
        "scraper.source_disabled",
        source_id=source.id,
        consecutive_failures=source.consecutive_failure_count
    )

db.commit()
```

**Behavior:**
- ✅ After 3 consecutive failures → `is_active = False`
- ✅ Disabled sources excluded from future jobs
- ✅ Logged with `scraper.source_disabled` event

---

### 6. ✅ Reset Counter on Success

**Issue:** Failure counter was never reset, so sources would eventually be disabled even with intermittent successes.

**Fix:**
```python
# In run() after successful scrape:
results = await self._scrape(page, source, db, location)
await self._check_html_hash(page, source, db)

# Reset failure counter on success
source.consecutive_failure_count = 0
db.commit()

logger.info(
    "scraper.completed",
    source_id=source.id,
    source_name=source.name,
    location=location,
    result_count=len(results)
)
```

**Behavior:**
- ✅ Every successful scrape resets counter to 0
- ✅ Only **consecutive** failures trigger auto-disable
- ✅ Source with 2 failures, 1 success, 3 failures = NOT disabled (counter reset)

---

## Updated Method Signatures

### run()
```python
# BEFORE
def run(self, source, db, location) -> list[dict]:

# AFTER
async def run(self, source, db, location) -> list[dict]:
```

### _apply_anti_bot_measures()
```python
# BEFORE
def _apply_anti_bot_measures(self) -> None:

# AFTER
async def _apply_anti_bot_measures(self, page) -> None:
```

### _check_html_hash()
```python
# BEFORE
async def _check_html_hash(self, source, db) -> None:

# AFTER
async def _check_html_hash(self, page, source, db) -> None:
```

### _handle_failure()
```python
# BEFORE
def _handle_failure(self, source, db, exception) -> None:

# AFTER
async def _handle_failure(self, page, source, db, exception) -> None:
```

### _detect_captcha()
```python
# BEFORE
def _detect_captcha(self) -> bool:

# AFTER
async def _detect_captcha(self, page) -> bool:
```

---

## Async Context Manager Pattern

### Why AsyncCamoufox Context Manager?

**Without context manager (old code):**
```python
browser = Camoufox(...)
page = browser.new_page()
try:
    # scraping
finally:
    page.close()  # ❌ Might fail
    browser.close()  # ❌ Might not be called if page.close() fails
```

**With context manager (new code):**
```python
async with AsyncCamoufox(...) as browser:
    context = await browser.new_context(...)
    page = await context.new_page()
    try:
        # scraping
    finally:
        await page.close()
        await context.close()
# ✅ Browser automatically closed even if exceptions occur
```

**Benefits:**
- ✅ Guaranteed cleanup
- ✅ No resource leaks
- ✅ Proper exception handling
- ✅ Follows Python best practices

---

## Auto-Disable Logic Flow

```
Scrape Attempt 1: FAIL → consecutive_failure_count = 1
Scrape Attempt 2: FAIL → consecutive_failure_count = 2
Scrape Attempt 3: FAIL → consecutive_failure_count = 3 → is_active = False ❌

OR

Scrape Attempt 1: FAIL → consecutive_failure_count = 1
Scrape Attempt 2: FAIL → consecutive_failure_count = 2
Scrape Attempt 3: SUCCESS → consecutive_failure_count = 0 ✅ (reset)
Scrape Attempt 4: FAIL → consecutive_failure_count = 1
Scrape Attempt 5: FAIL → consecutive_failure_count = 2
Scrape Attempt 6: FAIL → consecutive_failure_count = 3 → is_active = False ❌
```

**Key Point:** Only **consecutive** failures count. Any success resets the counter.

---

## Files Modified

1. **`backend/scrapers/base_scraper.py`**
   - Changed import from `camoufox.sync_api` to `camoufox.async_api`
   - Made `run()` async with AsyncCamoufox context manager
   - Removed `self.browser` and `self.page` instance variables
   - Made `_apply_anti_bot_measures()` async with page parameter
   - Made `_handle_failure()` async with page parameter
   - Updated `_check_html_hash()` to accept page parameter
   - Added auto-disable logic (3 consecutive failures)
   - Added counter reset on success

---

## Testing Checklist

### Verify Async Context Manager
```python
async def test_run_closes_browser():
    scraper = BookingComScraper()
    results = await scraper.run(source, db, "Kathmandu")
    # Browser should be closed automatically
    # No resource leaks
```

### Verify Auto-Disable
```python
async def test_auto_disable_after_3_failures():
    source.consecutive_failure_count = 0
    
    # Fail 3 times
    for i in range(3):
        try:
            await scraper.run(source, db, "Invalid")
        except:
            pass
    
    assert source.consecutive_failure_count == 3
    assert source.is_active == False
```

### Verify Counter Reset
```python
async def test_counter_reset_on_success():
    source.consecutive_failure_count = 2
    
    # Successful scrape
    results = await scraper.run(source, db, "Kathmandu")
    
    assert source.consecutive_failure_count == 0
    assert source.is_active == True
```

---

## Summary

✅ **run() is now fully async**  
✅ **AsyncCamoufox context manager prevents resource leaks**  
✅ **No instance variables for browser/page**  
✅ **All methods receive page as parameter**  
✅ **Auto-disable after 3 consecutive failures**  
✅ **Counter resets on success**  
✅ **Proper async/await throughout**  
✅ **Ready for Task 9**  

---

**Fixes Applied:** 2024-04-26  
**Files Modified:** 1 file (`base_scraper.py`)  
**Status:** ✅ Complete - All critical bugs fixed
