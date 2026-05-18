# Quick Start: Booking.com Detail Page Scraping

## 🚀 3-Step Setup

### Step 1: Apply Selectors (30 seconds)
```powershell
docker cp add_booking_detail_selectors.sql gen_scraper-postgres-1:/tmp/
docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -f /tmp/add_booking_detail_selectors.sql
```

### Step 2: Restart Services (30 seconds)
```powershell
docker-compose restart backend celery
```

### Step 3: Test (5 minutes)
1. Open http://localhost:5173
2. Create job: Booking.com → Kathmandu → 5 results → Hotels
3. Wait for completion
4. Check results:
```powershell
docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c "SELECT name, amenities IS NOT NULL as has_amenities, checkin_time FROM cleaned_results WHERE source_id = 1 ORDER BY created_at DESC LIMIT 5;"
```

## ✅ Success Criteria

You should see:
- ✅ `has_amenities`: true
- ✅ `checkin_time`: "From 14:00 to 23:30"
- ✅ Logs show: `scraper.detail_extraction_complete`

## 📊 What You Get

**Before (card data only):**
- Name, rating, price, address

**After (card + detail data):**
- Name, rating, price, address
- **+ Amenities** (Free WiFi, Restaurant, etc.)
- **+ Review scores** (Staff: 9.0, Location: 9.5)
- **+ Check-in/out times**
- **+ Languages spoken**
- **+ Full description**
- **+ Star rating**

## ⚙️ Configuration

Edit `.env` to tune:
```env
MAX_DETAIL_PAGES_PER_JOB=10      # How many detail pages to visit
DETAIL_PAGE_DELAY_MIN=3000        # Min delay (ms)
DETAIL_PAGE_DELAY_MAX=6000        # Max delay (ms)
```

## 🔍 Troubleshooting

**No detail data?**
```powershell
# Check if selectors were added
docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c "SELECT COUNT(*) FROM scraper_selectors WHERE field_name LIKE 'detail_%';"
# Should return 9

# Check logs
docker logs gen_scraper-celery-1 --tail 100 | Select-String "detail"
```

**CAPTCHA detected?**
- Normal! System returns partial results
- Reduce `MAX_DETAIL_PAGES_PER_JOB` to 5
- Increase delays to 4000-8000ms

## 📚 Full Documentation

- **Summary**: `BOOKING_DETAIL_SCRAPING_SUMMARY.md`
- **Technical**: `BOOKING_DETAIL_SCRAPING_IMPLEMENTATION.md`
- **Code**: `backend/scrapers/booking_com.py`

---

**Total Setup Time**: ~2 minutes  
**First Test**: ~5 minutes  
**Status**: ✅ Ready to use
