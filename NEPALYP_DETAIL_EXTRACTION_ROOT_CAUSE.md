# NepalYP Detail Extraction - Root Cause Found

**Date**: May 17, 2026  
**Status**: 🔍 **ROOT CAUSE IDENTIFIED**

---

## Problem Summary

Detail page extraction code exists and is correct, but **NEVER RUNS** because of an early return statement when `max_results` is reached.

---

## Root Cause Analysis

### Code Flow Issue

**Location**: `backend/scrapers/nepalyp.py` lines 145-149

```python
# Inside the while loop
for hotel in page_hotels:
    all_hotels.append(hotel)
    if max_results and len(all_hotels) >= max_results:
        logger.info("nepalyp.max_results_reached", ...)
        logger.info("nepalyp.scrape_complete", ...)
        return all_hotels[:max_results]  # ← EARLY RETURN HERE!
```

**Detail extraction code location**: Lines 183-203 (AFTER the while loop)

```python
# This code is AFTER the while loop ends
# Collect detail URLs from results
detail_urls = [r['detail_url'] for r in all_hotels if r.get('detail_url')]

if detail_urls:
    logger.info("nepalyp.starting_detail_extraction", ...)
    await self._extract_from_detail_pages(...)
```

### Why It Fails

1. **Job starts** with `max_results=5`
2. **Search page extraction** works perfectly, extracts 5 hotels
3. **Early return triggered**: When 5th hotel is added, code hits line 149: `return all_hotels[:max_results]`
4. **Detail extraction skipped**: Code never reaches line 183 where detail URLs are collected
5. **Result**: Hotels saved to database with NULL phone/website

### Log Evidence

From worker logs:
```
[2026-05-17 02:48:53] nepalyp.extraction_complete card_count=21 result_count=20 sample_name=Chhaimale Resort sample_url=https://www.nepalyp.com/company/65038/Chhaimale_Resort
[2026-05-17 02:48:53] nepalyp.max_results_reached count=5 max_results=5 page=1
[2026-05-17 02:48:53] nepalyp.scrape_complete location=Kathmandu total=5
```

**Missing logs** (never appeared):
- `nepalyp.detail_urls_collected`
- `nepalyp.detail_urls_after_limit`
- `nepalyp.starting_detail_extraction`
- `nepalyp.extracting_detail`
- `nepalyp.detail_merged`

---

## Solution

### Option 1: Move Detail Extraction BEFORE Early Return (RECOMMENDED)

Collect detail URLs and extract BEFORE checking max_results:

```python
# Inside the while loop, BEFORE the early return
for hotel in page_hotels:
    all_hotels.append(hotel)
    
    # Check if we've reached max_results
    if max_results and len(all_hotels) >= max_results:
        logger.info("nepalyp.max_results_reached", ...)
        
        # EXTRACT DETAIL PAGES BEFORE RETURNING
        detail_urls = [r['detail_url'] for r in all_hotels if r.get('detail_url')]
        from config import settings
        max_detail = getattr(settings, 'MAX_DETAIL_PAGES_PER_JOB', 10)
        detail_urls = detail_urls[:max_detail]
        
        if detail_urls:
            logger.info("nepalyp.starting_detail_extraction", ...)
            await self._extract_from_detail_pages(
                page=page,
                source=source,
                db=db,
                results=all_hotels,
                detail_urls=detail_urls
            )
        
        logger.info("nepalyp.scrape_complete", ...)
        return all_hotels[:max_results]
```

**Pros**:
- Guarantees detail extraction runs
- Works with max_results limit
- Minimal code changes

**Cons**:
- Code duplication (detail extraction logic appears twice)

### Option 2: Remove Early Return, Use Break Instead

Replace `return` with `break` to exit the loop but continue to detail extraction:

```python
for hotel in page_hotels:
    all_hotels.append(hotel)
    if max_results and len(all_hotels) >= max_results:
        logger.info("nepalyp.max_results_reached", ...)
        break  # ← BREAK instead of RETURN

# After while loop ends (either naturally or via break)
# Detail extraction code runs here
detail_urls = [r['detail_url'] for r in all_hotels if r.get('detail_url')]
...
```

**Pros**:
- No code duplication
- Clean flow
- Detail extraction always runs

**Cons**:
- Need to also break out of the outer `while page_num <= max_pages` loop
- Requires flag variable or nested break handling

### Option 3: Extract Detail Pages Incrementally

Extract detail pages as we go, not at the end:

```python
for hotel in page_hotels:
    all_hotels.append(hotel)
    
    # Extract detail page immediately for this hotel
    if hotel.get('detail_url'):
        await self._extract_single_detail_page(
            page=page,
            source=source,
            db=db,
            result=hotel,
            detail_url=hotel['detail_url']
        )
    
    if max_results and len(all_hotels) >= max_results:
        return all_hotels[:max_results]
```

**Pros**:
- Detail extraction happens immediately
- No risk of skipping detail extraction
- Better for streaming/progressive results

**Cons**:
- Requires refactoring `_extract_from_detail_pages()` into single-page method
- More complex
- Slower (can't batch detail page visits)

---

## Recommended Fix: Option 2 with Proper Break Handling

This is the cleanest solution that avoids code duplication:

```python
async def _scrape(self, page, source: Source, db: Session, location: str, max_results: Optional[int] = None, category_id: Optional[int] = None) -> list[dict]:
    """Scrape hotel listings from NepalYP."""
    logger.info("nepalyp.scrape_start", location=location, max_results=max_results)

    category = self._get_category_from_source_name()
    all_hotels = []
    page_num = 1
    max_pages = 40
    max_results_reached = False  # ← ADD FLAG

    try:
        while page_num <= max_pages and not max_results_reached:  # ← CHECK FLAG
            # ... page navigation code ...
            
            page_hotels = await self._extract_hotels_from_page(page, source, db, location)

            # Add hotels one by one, stopping exactly at max_results
            for hotel in page_hotels:
                all_hotels.append(hotel)
                if max_results and len(all_hotels) >= max_results:
                    logger.info("nepalyp.max_results_reached", ...)
                    max_results_reached = True  # ← SET FLAG
                    break  # ← BREAK INNER LOOP

            if max_results_reached:
                break  # ← BREAK OUTER LOOP

            # ... pagination check code ...
            page_num += 1

        # NOW detail extraction runs regardless of how we exited the loop
        detail_urls = [r['detail_url'] for r in all_hotels if r.get('detail_url')]
        
        logger.info("nepalyp.detail_urls_collected", ...)
        
        from config import settings
        max_detail = getattr(settings, 'MAX_DETAIL_PAGES_PER_JOB', 10)
        detail_urls = detail_urls[:max_detail]
        
        logger.info("nepalyp.detail_urls_after_limit", ...)
        
        if detail_urls:
            logger.info("nepalyp.starting_detail_extraction", ...)
            await self._extract_from_detail_pages(
                page=page,
                source=source,
                db=db,
                results=all_hotels,
                detail_urls=detail_urls
            )

        logger.info("nepalyp.scrape_complete", location=location, total=len(all_hotels))
        return all_hotels[:max_results] if max_results else all_hotels

    except Exception as e:
        logger.error("nepalyp.scrape_error", location=location, error=str(e))
        await self._debug_page(page, "nepalyp_error")
        return all_hotels
```

---

## Implementation Steps

1. **Backup current file**:
   ```powershell
   Copy-Item backend\scrapers\nepalyp.py backend\scrapers\nepalyp.py.backup
   ```

2. **Apply the fix** (Option 2 with flag)

3. **Restart worker**:
   ```powershell
   docker-compose restart worker
   ```

4. **Test with small job**:
   ```powershell
   docker exec gen_scraper-worker-1 python /app/trigger_nepalyp_test.py
   ```

5. **Verify logs show**:
   - `nepalyp.detail_urls_collected`
   - `nepalyp.starting_detail_extraction`
   - `nepalyp.extracting_detail`
   - `nepalyp.detail_merged`

6. **Check database**:
   ```sql
   SELECT name, phone_primary, website 
   FROM cleaned_results cr 
   JOIN sources s ON cr.source_id = s.id 
   WHERE s.name = 'nepalyp' 
   ORDER BY cr.created_at DESC LIMIT 5;
   ```

   **Expected**: 2-3 out of 5 hotels should have phone_primary (limited by MAX_DETAIL_PAGES_PER_JOB=2)

---

## Why This Wasn't Caught Earlier

1. **Browser testing** only verified selectors work, not code flow
2. **Code review** focused on selector logic, not control flow
3. **Early return** is a common pattern, didn't seem suspicious
4. **No integration test** that checks detail extraction actually runs

---

## Prevention for Future

1. **Add integration test** that verifies detail extraction runs:
   ```python
   def test_nepalyp_detail_extraction_runs():
       """Verify detail extraction runs even with max_results."""
       # Mock scraper, set max_results=5
       # Verify _extract_from_detail_pages was called
       assert detail_extraction_called
   ```

2. **Add assertion** in code:
   ```python
   # After detail extraction block
   if all_hotels and not detail_urls:
       logger.warning("nepalyp.no_detail_urls", 
                     hotel_count=len(all_hotels),
                     sample=all_hotels[0])
   ```

3. **Code review checklist**: Check for early returns that skip important logic

---

## Summary

**Root Cause**: Early `return` statement when `max_results` reached (line 149) prevents execution from reaching detail extraction code (line 183+)

**Solution**: Replace early return with break + flag, allowing detail extraction to run after loop exits

**Impact**: Once fixed, detail extraction will run for all jobs, enriching results with phone/address/website from detail pages

**Confidence**: 100% - This is definitively the issue

