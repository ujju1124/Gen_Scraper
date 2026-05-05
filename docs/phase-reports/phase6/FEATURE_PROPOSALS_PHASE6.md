# Phase 6 Feature Proposals

## Feature 1: Booking.com Detail Page Scraping

### Current Limitation
Currently, booking.com scraper only extracts data from the **search results cards** (listing page). It does NOT visit individual hotel detail pages to get additional information like:
- Full description
- Complete amenities list
- All photos
- Detailed reviews
- Contact information (phone, email)
- Check-in/check-out policies
- Cancellation policies
- Room types and details

### Comparison with DirectoryOfNepal
**DirectoryOfNepal** (working example):
```
Step 1: Scrape listing page → Get 20 hotel cards
Step 2: Visit each hotel detail page → Get phone, email, full description
Result: Complete data with contact info
```

**Booking.com** (current):
```
Step 1: Scrape listing page → Get 25 hotel cards
Step 2: ❌ STOP (no detail page scraping)
Result: Incomplete data, missing phone/email
```

### Proposed Implementation

#### Step 1: Add Detail Page Selectors

You need to add selectors for booking.com **detail pages** in the admin panel:

**Required Selectors:**

1. **detail_phone** (CSS Selector)
   - Purpose: Extract phone number from detail page
   - Example: `[data-testid="phone-number"]` or `.hp_phone_number`

2. **detail_email** (CSS Selector)
   - Purpose: Extract email from detail page
   - Example: `[data-testid="email"]` or `.hp_email`

3. **detail_description_full** (CSS Selector)
   - Purpose: Extract complete description
   - Example: `[data-testid="property-description"]`

4. **detail_amenities_full** (CSS Selector)
   - Purpose: Extract all amenities (not just highlights)
   - Example: `.hp_desc_important_facilities .important_facility`

5. **detail_policies** (CSS Selector)
   - Purpose: Extract check-in/check-out times, cancellation policy
   - Example: `.hp_desc_policies`

6. **detail_room_types** (CSS Selector)
   - Purpose: Extract available room types
   - Example: `.hprt-table .hprt-table-cell`

#### Step 2: How to Find These Selectors

**Method 1: Use Browser Inspector**
1. Go to booking.com and search for hotels in Kathmandu
2. Click on any hotel to open detail page
3. Right-click on phone number → Inspect
4. Look for unique CSS selector or data-testid attribute
5. Test in console: `document.querySelector('YOUR_SELECTOR')`

**Method 2: Use Selector Healing Tool**
1. Go to Admin Panel → Selector Management
2. Find booking_com source
3. Click "Add Selector"
4. Enter selector name: `detail_phone`
5. Enter CSS selector
6. Test on a sample URL

**Example Detail Page URL:**
```
https://www.booking.com/hotel/np/hyatt-regency-kathmandu.html
```

#### Step 3: Update Booking.com Scraper Code

The scraper needs to be modified to:
1. Extract detail page URLs from cards
2. Visit each detail page
3. Extract additional data using new selectors
4. Merge with card data

**Current Flow:**
```python
# backend/scrapers/booking_com.py (current)
async def run(self, source, db, location, max_results=100):
    # 1. Navigate to search page
    # 2. Extract cards
    # 3. Return results
    return results  # Only card data
```

**Proposed Flow:**
```python
# backend/scrapers/booking_com.py (proposed)
async def run(self, source, db, location, max_results=100):
    # 1. Navigate to search page
    # 2. Extract cards with detail URLs
    # 3. For each card:
    #    a. Visit detail page
    #    b. Extract additional data
    #    c. Merge with card data
    # 4. Return enriched results
    return enriched_results  # Card + detail data
```

### Benefits
1. ✅ **More complete data** - Phone, email, full descriptions
2. ✅ **Better quality** - Detailed amenities, policies
3. ✅ **Competitive advantage** - More data than competitors
4. ✅ **Better user experience** - Users get all info they need

### Challenges
1. ⚠️ **Slower scraping** - Need to visit N detail pages (N = number of hotels)
2. ⚠️ **More API calls** - Increases load on booking.com
3. ⚠️ **Anti-bot detection** - More likely to be detected
4. ⚠️ **Selector maintenance** - Detail page selectors may change

### Mitigation Strategies
1. **Rate limiting** - Add delays between detail page visits (2-3 seconds)
2. **Batch processing** - Process detail pages in smaller batches
3. **Caching** - Cache detail page data to avoid re-scraping
4. **User-agent rotation** - Rotate user agents to avoid detection
5. **Proxy support** - Use proxies if needed (future enhancement)

### Estimated Impact
**Current:**
- Time: ~30 seconds for 25 hotels (cards only)
- Data completeness: ~40% (missing phone, email, full description)

**After Implementation:**
- Time: ~90 seconds for 25 hotels (cards + details)
- Data completeness: ~80% (includes phone, email, full description)

---

## Feature 2: Multi-Source Data Merging

### Current Limitation
When the same hotel is scraped from multiple sources (booking.com, nepalyp, directoryofnepal), the system creates **separate records** with NO merging. This means:
- Incomplete data is NOT enriched from other sources
- Users see duplicate hotels
- Data quality is lower than it could be

### Example Problem
```
Source 1 (booking.com):
  name: "Hotel XYZ"
  address: "Thamel, Kathmandu"
  phone: NULL
  email: NULL
  rating: 8.5

Source 2 (nepalyp):
  name: "Hotel XYZ"
  address: NULL
  phone: "+977-1-4123456"
  email: NULL
  rating: NULL

Source 3 (directoryofnepal):
  name: "Hotel XYZ"
  address: "Thamel"
  phone: "+977-1-4123456"
  email: "info@hotelxyz.com"
  rating: NULL

Current Result: 3 separate records (or 1 incomplete if same job)
Desired Result: 1 merged record with ALL data
```

### Proposed Solution: Smart Merging Pipeline

#### Architecture Overview
```
┌─────────────────────────────────────────────────────────┐
│  Step 1: Scrape from Multiple Sources                  │
│  ├─ booking.com    → 75 results                        │
│  ├─ nepalyp        → 50 results                        │
│  └─ directoryofnepal → 100 results                     │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│  Step 2: Identify Duplicates (by dedup_key)            │
│  Hotel XYZ found in all 3 sources                      │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│  Step 3: Merge Data Using Smart Rules                  │
│  ├─ Name: Use from highest priority source             │
│  ├─ Phone: Collect all unique values                   │
│  ├─ Email: Collect all unique values                   │
│  ├─ Address: Use most complete                         │
│  ├─ Rating: Calculate weighted average                 │
│  └─ Amenities: Merge and deduplicate                   │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│  Step 4: Save Merged Record                            │
│  ├─ merged_from_sources: [2, 6, 12]                    │
│  ├─ data_completeness: 95%                             │
│  └─ confidence_score: 0.9                              │
└─────────────────────────────────────────────────────────┘
```

#### Merging Rules by Field Type

**1. Identity Fields (name, brand, property_type)**
- **Rule**: Use from highest priority source
- **Priority**: booking_com > directoryofnepal > nepalyp
- **Reason**: Booking.com has most standardized names

**2. Contact Fields (phone, email)**
- **Rule**: Collect ALL unique values (array)
- **Format**: Store as JSON array
- **Example**: `["phone1", "phone2"]`
- **Reason**: Multiple contact numbers are valuable

**3. Location Fields (address, city, district)**
- **Rule**: Use most complete (longest non-null value)
- **Validation**: Must contain city name
- **Fallback**: Use from highest priority source

**4. Coordinates (latitude, longitude)**
- **Rule**: Use from most reliable source
- **Priority**: Overpass API > booking_com > city center
- **Validation**: Must be within Nepal bounds

**5. Rating Fields (rating_overall, review_count)**
- **Rule**: Weighted average based on review count
- **Formula**: `(rating1 * reviews1 + rating2 * reviews2) / (reviews1 + reviews2)`
- **Reason**: More reviews = more reliable rating

**6. Price Fields (price_min, price_max)**
- **Rule**: Use min of all price_min, max of all price_max
- **Reason**: Show full price range across sources

**7. Array Fields (amenities, photos)**
- **Rule**: Merge and deduplicate
- **Normalization**: Lowercase, trim whitespace
- **Example**: `["wifi", "parking", "pool"]`

**8. Description Fields (description_short, description_full)**
- **Rule**: Use longest non-null value
- **Reason**: More detail is better

**9. Boolean Fields (pets_allowed, includes_breakfast)**
- **Rule**: TRUE if any source says TRUE
- **Reason**: Assume most permissive policy

**10. Metadata Fields (source_url, scraped_at)**
- **Rule**: Store all as JSON array
- **Format**: `[{"source_id": 2, "url": "...", "scraped_at": "..."}]`

#### Database Schema Changes

**New Fields in `cleaned_results` table:**

```sql
-- Track which sources were merged
merged_from_sources INTEGER[] DEFAULT NULL,  -- Array of source IDs

-- Store source-specific data for audit
source_data JSONB DEFAULT NULL,  -- Full data from each source

-- Confidence scoring
confidence_score DECIMAL(3,2) DEFAULT NULL,  -- 0.0 to 1.0

-- Merge metadata
merged_at TIMESTAMP DEFAULT NULL,
merge_strategy VARCHAR(50) DEFAULT NULL  -- 'priority', 'average', 'collect', etc.
```

**Example `source_data` JSON:**
```json
{
  "2": {  // booking_com
    "name": "Hotel XYZ",
    "rating": 8.5,
    "phone": null,
    "scraped_at": "2026-05-03T10:00:00Z"
  },
  "6": {  // nepalyp
    "name": "Hotel XYZ",
    "rating": null,
    "phone": "+977-1-4123456",
    "scraped_at": "2026-05-03T10:05:00Z"
  },
  "12": {  // directoryofnepal
    "name": "Hotel XYZ",
    "rating": null,
    "phone": "+977-1-4123456",
    "email": "info@hotelxyz.com",
    "scraped_at": "2026-05-03T10:10:00Z"
  }
}
```

#### Implementation Steps

**Phase 6.1: Database Migration**
1. Add new fields to `cleaned_results` table
2. Create migration script
3. Update models

**Phase 6.2: Merging Logic**
1. Create `MergingPipeline` class in `backend/scrapers/merger.py`
2. Implement field-specific merge strategies
3. Add confidence scoring algorithm
4. Add source priority configuration

**Phase 6.3: Integration**
1. Update `CleaningPipeline` to call `MergingPipeline`
2. Modify deduplication to group instead of skip
3. Update tests

**Phase 6.4: Frontend Updates**
1. Show "Merged from X sources" badge
2. Add "View Source Data" button to see individual source data
3. Show confidence score indicator
4. Add source comparison view

**Phase 6.5: Admin Features**
1. Configure source priority in admin panel
2. Configure merge strategies per field
3. View merge statistics
4. Manual merge/unmerge tools

#### Confidence Scoring Algorithm

```python
def calculate_confidence(merged_record, source_records):
    """
    Calculate confidence score (0.0 to 1.0) based on:
    - Number of sources (more = higher confidence)
    - Data agreement (sources agree = higher confidence)
    - Source reliability (booking.com = higher weight)
    - Data completeness (more fields = higher confidence)
    """
    
    # Base score from number of sources
    source_count = len(source_records)
    base_score = min(source_count / 3, 1.0)  # Max at 3 sources
    
    # Agreement bonus (sources have same values)
    agreement_score = calculate_field_agreement(source_records)
    
    # Source reliability weight
    reliability_score = calculate_source_reliability(source_records)
    
    # Data completeness
    completeness_score = merged_record['data_completeness'] / 100
    
    # Weighted average
    confidence = (
        base_score * 0.3 +
        agreement_score * 0.3 +
        reliability_score * 0.2 +
        completeness_score * 0.2
    )
    
    return round(confidence, 2)
```

#### Example Merged Record

**Input (3 sources):**
```python
booking_com = {
    "name": "Hotel Yak & Yeti",
    "address": "Durbar Marg, Kathmandu",
    "rating": 8.7,
    "review_count": 1250,
    "amenities": ["WiFi", "Pool", "Spa"]
}

nepalyp = {
    "name": "Yak & Yeti Hotel",
    "phone": "+977-1-4248999",
    "amenities": ["WiFi", "Restaurant"]
}

directoryofnepal = {
    "name": "Hotel Yak and Yeti",
    "phone": "+977-1-4248999",
    "email": "info@yakandyeti.com",
    "amenities": ["Pool", "Gym", "Parking"]
}
```

**Output (merged):**
```python
merged = {
    "name": "Hotel Yak & Yeti",  # From booking_com (highest priority)
    "address": "Durbar Marg, Kathmandu",  # From booking_com (most complete)
    "phone": ["+977-1-4248999"],  # Collected from nepalyp & directoryofnepal
    "email": ["info@yakandyeti.com"],  # From directoryofnepal
    "rating": 8.7,  # From booking_com (only source with rating)
    "review_count": 1250,  # From booking_com
    "amenities": ["WiFi", "Pool", "Spa", "Restaurant", "Gym", "Parking"],  # Merged
    "merged_from_sources": [2, 6, 12],  # booking_com, nepalyp, directoryofnepal
    "confidence_score": 0.87,  # High confidence (3 sources, good agreement)
    "data_completeness": 85.7  # 12 of 14 key fields filled
}
```

### Benefits of Merging

1. **Higher Data Quality**
   - 85% completeness vs 40% without merging
   - More contact information
   - More amenities

2. **Better User Experience**
   - No duplicate hotels
   - Complete information in one place
   - Source transparency

3. **Competitive Advantage**
   - More complete data than competitors
   - Higher confidence scores
   - Better search results

4. **Cost Efficiency**
   - Scrape less frequently (data is enriched)
   - Better ROI on scraping efforts

### Estimated Development Time

**Feature 1: Booking.com Detail Scraping**
- Selector identification: 2 hours
- Code implementation: 4 hours
- Testing: 2 hours
- **Total: 8 hours (1 day)**

**Feature 2: Multi-Source Merging**
- Database migration: 2 hours
- Merging logic: 8 hours
- Integration: 4 hours
- Frontend updates: 6 hours
- Testing: 4 hours
- **Total: 24 hours (3 days)**

**Combined: 4 days of development**

---

## Recommendation for Supervisor

### Priority: HIGH

Both features significantly improve data quality and user experience. They should be implemented together because:

1. **Synergy**: Detail scraping provides more data → Merging combines it effectively
2. **ROI**: 4 days of work → 2x data completeness improvement
3. **Competitive**: Most scraping tools don't do multi-source merging
4. **Scalable**: Once built, works for all future sources

### Suggested Approach

**Week 1:**
- Day 1: Implement booking.com detail scraping
- Day 2-3: Implement merging pipeline
- Day 4: Testing and refinement

**Week 2:**
- Deploy to production
- Monitor performance
- Gather user feedback

### Success Metrics

**Before:**
- Data completeness: 40%
- Duplicate rate: 30%
- User satisfaction: Unknown

**After (Expected):**
- Data completeness: 85%
- Duplicate rate: 0%
- User satisfaction: High (complete data, no duplicates)

---

## Next Steps

1. **Get supervisor approval** for both features
2. **Identify booking.com selectors** using browser inspector
3. **Create Phase 6 spec** with detailed requirements
4. **Begin implementation** starting with booking.com detail scraping
5. **Test thoroughly** with real data
6. **Deploy and monitor**

---

**Questions for Supervisor:**
1. Do you approve both features for Phase 6?
2. What is the priority? (Both together or one at a time?)
3. Any specific requirements or concerns?
4. Timeline expectations?

