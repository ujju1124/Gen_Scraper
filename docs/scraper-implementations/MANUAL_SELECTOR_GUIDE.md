# Manual Selector Implementation Guide

This guide explains how to provide CSS selectors for the scrapers that are currently in "HUMAN CHECKPOINT" mode.

---

## Categories in the Project

We have **30 categories** in total:

### Accommodation (5 categories)
1. **Hotels** (`hotels`)
2. **Hostels** (`hostels`)
3. **Guesthouses** (`guesthouses`)
4. **Resorts** (`resorts`)
5. **Lodges** (`lodges`)

### Food & Dining (3 categories)
6. **Restaurants** (`restaurants`)
7. **Cafes** (`cafes`)
8. **Bakeries** (`bakeries`)

### Healthcare (4 categories)
9. **Pharmacies** (`pharmacies`)
10. **Hospitals** (`hospitals`)
11. **Clinics** (`clinics`)
12. **Dental Clinics** (`dental_clinics`)

### Financial (2 categories)
13. **Banks** (`banks`)
14. **ATMs** (`atms`)

### Transportation (3 categories)
15. **Petrol Stations** (`petrol_stations`)
16. **Car Rentals** (`car_rentals`)
17. **Bus Stations** (`bus_stations`)

### Retail (1 category)
18. **Supermarkets** (`supermarkets`)

### Education (2 categories)
19. **Schools** (`schools`)
20. **Colleges** (`colleges`)

### Government & Services (4 categories)
21. **Government Offices** (`government_offices`)
22. **Police Stations** (`police_stations`)
23. **Fire Stations** (`fire_stations`)
24. **Embassies** (`embassies`)

### Tourism (2 categories)
25. **Trekking Agencies** (`trekking_agencies`)
26. **Travel Agencies** (`travel_agencies`)

### Culture & Recreation (4 categories)
27. **Temples** (`temples`)
28. **Museums** (`museums`)
29. **Parks** (`parks`)
30. **Gyms** (`gyms`)

---

## Scrapers Awaiting Selectors

### Hotels Category
1. **Agoda** (`agoda.py`) - Playwright (React SPA)
2. **OYO Rooms** (`oyo_rooms.py`) - Playwright (React SPA)
3. **eSewa Hotels** (`esewa_hotels.py`) - Playwright (React SPA)
4. **Hostelworld** (`hostelworld.py`) - Playwright
5. **DirectoryOfNepal Hotels** (`directoryofnepal.py`) - httpx + BeautifulSoup (static HTML)

### Restaurants Category
6. **Foodmandu** (`foodmandu.py`) - Playwright (React SPA)
7. **NepalYP Restaurants** (uses `nepalyp.py`) - httpx + BeautifulSoup
8. **DirectoryOfNepal Restaurants** (uses `directoryofnepal.py`) - httpx + BeautifulSoup

### Pharmacies Category
9. **NepalYP Pharmacies** (uses `nepalyp.py`) - httpx + BeautifulSoup
10. **NepalYP Drugstores** (uses `nepalyp.py`) - httpx + BeautifulSoup
11. **DirectoryOfNepal Pharmacies** (uses `directoryofnepal.py`) - httpx + BeautifulSoup

### Hospitals Category
12. **HamroDoctor Hospitals** (`hamrodoctor.py`) - Playwright
13. **HamroDoctor Clinics** (uses `hamrodoctor.py`) - Playwright
14. **NepalYP Hospitals** (uses `nepalyp.py`) - httpx + BeautifulSoup

---

## What Information I Need From You

For each scraper, I need CSS selectors for the following fields:

### Required Fields (Core Data)
1. **name** - Business/hotel name
2. **address** - Full address
3. **city** - City name
4. **phone** - Phone number
5. **source_url** - Link to the detail page

### Optional Fields (Enhanced Data)
6. **email** - Email address
7. **website** - Website URL
8. **rating_overall** - Overall rating (e.g., 8.5/10)
9. **review_count** - Number of reviews
10. **price_min** - Minimum price
11. **price_max** - Maximum price
12. **currency** - Currency code (NPR, USD, etc.)
13. **thumbnail_url** - Image URL
14. **description** - Short description
15. **amenities** - List of amenities/features
16. **latitude** - Latitude coordinate
17. **longitude** - Longitude coordinate

---

## Format for Providing Selectors

### Option 1: Simple Format (Recommended)
```
SCRAPER: Agoda
URL: https://www.agoda.com/search?city=Kathmandu

SELECTORS:
name: .PropertyCard__HotelName
address: .PropertyCard__Address
city: .PropertyCard__City
phone: .PropertyCard__Phone
rating_overall: .Review__Score
review_count: .Review__Count
price_min: .PropertyCard__PriceDisplay
source_url: .PropertyCard__Link (attribute: href)
thumbnail_url: .PropertyCard__Image (attribute: src)
```

### Option 2: JSON Format (For Complex Selectors)
```json
{
  "scraper": "Agoda",
  "url": "https://www.agoda.com/search?city=Kathmandu",
  "selectors": {
    "name": {
      "selector": ".PropertyCard__HotelName",
      "type": "css"
    },
    "address": {
      "selector": ".PropertyCard__Address",
      "type": "css"
    },
    "price_min": {
      "selector": ".PropertyCard__PriceDisplay",
      "type": "css",
      "attribute": "data-price"
    },
    "source_url": {
      "selector": ".PropertyCard__Link",
      "type": "css",
      "attribute": "href"
    }
  }
}
```

### Option 3: Table Format (For Multiple Scrapers)
```
| Field          | Agoda Selector              | OYO Selector           | eSewa Selector        |
|----------------|----------------------------|------------------------|----------------------|
| name           | .PropertyCard__HotelName   | .oyo-card__name        | .hotel-title         |
| address        | .PropertyCard__Address     | .oyo-card__address     | .hotel-address       |
| rating_overall | .Review__Score             | .oyo-rating            | .rating-value        |
| price_min      | .PropertyCard__PriceDisplay| .oyo-price             | .price-amount        |
```

---

## How to Find Selectors

### Method 1: Browser DevTools (Recommended)
1. Open the website in Chrome/Firefox
2. Right-click on the element → "Inspect"
3. Look for unique classes, IDs, or data attributes
4. Test the selector in Console: `document.querySelector('.your-selector')`

### Method 2: Using Browser Extensions
- **SelectorGadget** (Chrome) - Click elements to generate selectors
- **ChroPath** (Chrome/Firefox) - Generate XPath and CSS selectors

### Method 3: Network Tab (For API-based sites)
1. Open DevTools → Network tab
2. Filter by "XHR" or "Fetch"
3. Look for API endpoints returning JSON data
4. If found, provide the API endpoint instead of CSS selectors

---

## Selector Best Practices

### ✅ Good Selectors (Stable)
- `[data-testid="hotel-name"]` - Data attributes
- `.hotel-card__title` - BEM-style classes
- `#hotel-123` - Unique IDs
- `.PropertyCard > h3` - Specific structure

### ❌ Bad Selectors (Fragile)
- `.css-1a2b3c4` - Auto-generated classes
- `div > div > div > span` - Too generic
- `.text-lg.font-bold` - Utility classes (Tailwind)
- `body > div:nth-child(5)` - Position-based

---

## Example: Complete Selector Set

Here's a complete example for a fictional scraper:

```
SCRAPER: ExampleHotels
URL: https://example.com/hotels?city=Kathmandu

SELECTORS:
name: .hotel-card__title
address: .hotel-card__address
city: .hotel-card__city
phone: .hotel-card__phone
email: .hotel-card__email
website: .hotel-card__website (attribute: href)
rating_overall: .hotel-card__rating
review_count: .hotel-card__reviews
price_min: .hotel-card__price
currency: NPR (hardcoded)
thumbnail_url: .hotel-card__image (attribute: src)
source_url: .hotel-card__link (attribute: href)
description: .hotel-card__description

PAGINATION:
type: page-based
next_button: .pagination__next
max_pages: 10

NOTES:
- Prices are in NPR
- Rating is out of 10
- Some hotels don't have email/website
```

---

## What Happens After You Provide Selectors

1. I'll update the scraper file with your selectors
2. Remove the `# HUMAN CHECKPOINT` block
3. Implement the actual scraping logic
4. Add the selectors to the database (if using AUTO heal mode)
5. Set `is_active=True` for the source
6. Run tests to verify the scraper works

---

## Priority Order (Which Scrapers to Start With)

### High Priority (Hotels - Most Requested)
1. **Agoda** - Large inventory, popular
2. **OYO Rooms** - Budget hotels
3. **Hostelworld** - Backpacker hostels

### Medium Priority (Restaurants)
4. **Foodmandu** - Popular food delivery
5. **NepalYP Restaurants** - Local directory

### Lower Priority (Healthcare)
6. **HamroDoctor** - Medical directory
7. **NepalYP Pharmacies** - Pharmacy listings

---

## Questions to Answer

Before providing selectors, please tell me:

1. **Which scraper(s) do you want to implement first?**
   - Example: "Let's start with Agoda"

2. **Do you have access to these websites?**
   - Some sites may be geo-restricted

3. **What format do you prefer?**
   - Simple text format
   - JSON format
   - Table format

4. **Do you want me to help you find selectors?**
   - I can guide you through the process
   - Or you can provide them directly

---

## Ready to Start?

Just tell me:
1. Which scraper to start with
2. Provide the selectors in any format above
3. I'll implement it immediately!

Example response:
```
Let's start with Agoda.

SELECTORS:
name: .PropertyCard__HotelName
address: .PropertyCard__Address
...
```

---

## Need Help Finding Selectors?

If you need help, you can:
1. Share a screenshot of the website
2. Share the HTML snippet of a listing
3. Share the page URL and I'll guide you through finding selectors
4. Use browser DevTools and paste the HTML structure

I'm ready when you are! 🚀
