# Complete Project Brief for Kiro — Web Scraping Portal (v2)

Read this entire document before writing a single line of code. Every decision in this project has been pre-made deliberately. Do not substitute your own preferences, do not use alternative libraries, and do not skip phases. When something feels complex, refer to the reference sources listed at the end before asking or guessing.

---

## What You Are Building

A production-grade web portal that scrapes hotel and business data from multiple websites across Nepal. A user selects a category and location, triggers a scrape, and the system collects data in the background. An admin reviews results in a table, edits if needed, and pushes approved records to a final PostgreSQL database.

This system must work reliably for years. Design every decision with that in mind.

### Legal Notice

Scraping Booking.com, TripAdvisor, Agoda, and OYO Rooms may conflict with their Terms of Service. Before deploying this system for commercial or client use, obtain legal review or written permission from those platforms. This document is a technical specification only and does not constitute legal advice. For government and directory sources (Nepal Tourism Board, NepalYP, Nepal Police, DDA) there is no such restriction, but always respect `robots.txt` and implement polite rate delays regardless.

---

## Hard Rules — Read Before Writing Any Code

These rules are non-negotiable. Violating them creates bugs that are extremely difficult to fix later.

1. Never hardcode a selector in a Python scraper file. All selectors live in the `scraper_selectors` database table. Scrapers read from the database at runtime.
2. Never modify or delete a row in `raw_results` after it has been inserted. It is an append-only audit log.
3. The Celery task receives only `job_id`. It reads all other parameters from the database using that ID. Never pass location, category, or source_ids from the HTTP request to the Celery task.
4. Never trust the role from the JWT payload for authorisation. Always load the user's current role from the database on every protected request.
5. Never store the JWT in `localStorage` or `sessionStorage`. Use `httpOnly` secure cookies with `SameSite=Lax`. See the Authentication section for the full pattern.
6. The `POST /auth/register` endpoint must never accept a `role` parameter. All registrations create `role: user` only.
7. The admin password in the seed script must be read from an environment variable. Never hardcode a default password.
8. Never run a real scraper until the fake Celery task pipeline is fully working end-to-end. This is non-negotiable.
9. For Booking.com, TripAdvisor, Agoda, and OYO — always use Camoufox as the browser, not standard Playwright Chromium.
10. For simple HTML sources with no JavaScript (NepalYP, Nepal Tourism Board, Nepal Police, NOC, DDA) — use plain `httpx` with BeautifulSoup. Do not use a browser for these.
11. Always URL-encode the `location` parameter before injecting it into any scraper search URL. Use `urllib.parse.quote_plus(location)`.
12. All API list endpoints must be paginated. No endpoint may return an unbounded list. Default page size is 50, maximum is 200.
13. Always add database indexes for every column that appears in a `WHERE`, `ORDER BY`, or `JOIN` clause. See the Database Indexes section.
14. Cross-job deduplication is mandatory. Before inserting a `cleaned_results` row, check if a record with the same SHA-256(lowercase(name) + lowercase(city)) already exists in `cleaned_results` for the same `category_id`. If a match exists, skip insertion and log the duplicate.

---

## Technology Stack

Use exactly these tools. Do not substitute.

| Layer | Technology |
|---|---|
| Frontend | React + Vite |
| Frontend table | TanStack Table v8 |
| HTTP client (frontend) | Axios |
| Backend | FastAPI (Python) |
| Authentication | httpOnly cookie + JWT (python-jose, passlib[bcrypt]) + refresh tokens |
| Task queue | Celery + Redis |
| Real-time job updates | Server-Sent Events (SSE) via FastAPI `StreamingResponse` |
| Browser automation (protected sites) | Camoufox (wraps Playwright's Firefox) |
| Browser automation (simple sites) | httpx + BeautifulSoup |
| Crawling framework | Crawlee Python (wraps Camoufox/Playwright) |
| Database | PostgreSQL |
| ORM and migrations | SQLAlchemy + Alembic |
| Logging | structlog (structured JSON logs) |
| Error tracking | Sentry (sentry-sdk[fastapi]) |
| Rate limiting | slowapi |
| Containerisation | Docker + Docker Compose |
| Deployment | Railway (paid Hobby tier minimum — free tier RAM is insufficient for browser workers) |

---

## Architecture

```
React Frontend
     ↕ HTTPS (httpOnly cookie)
FastAPI Backend
     ├── SSE endpoint for real-time job status
     ↕
Celery Workers ←→ Redis (broker + result backend)
     ↕
Camoufox/Crawlee Scrapers   (JS-heavy protected sites)
httpx/BeautifulSoup Scrapers (static HTML sites)
     ↕
PostgreSQL Database
     ↕ (async writes)
structlog → stdout (Railway log drain) + Sentry (errors)
```

All services run in Docker containers managed by Docker Compose. The worker container must have `shm_size: 1gb` configured — Firefox requires shared memory or it crashes silently. On Railway, set `PLAYWRIGHT_SHM_SIZE=1073741824` and use a custom entrypoint that mounts `/dev/shm`.

---

## Authentication Pattern

**Do not use in-memory JWT or localStorage.** Use `httpOnly` cookies with access + refresh tokens. This is secure against XSS (cookie is inaccessible to JavaScript) and survives page refreshes.

### Token pair

| Token | Storage | Expiry | Purpose |
|---|---|---|---|
| Access token | `httpOnly` cookie (`access_token`) | 15 minutes | Authenticate API requests |
| Refresh token | `httpOnly` cookie (`refresh_token`) | 7 days | Obtain new access token silently |

### Cookie settings (both tokens)

```python
response.set_cookie(
    key="access_token",
    value=token,
    httponly=True,
    secure=True,          # HTTPS only in production
    samesite="lax",       # CSRF protection
    max_age=900,          # 15 minutes
    path="/",
)
```

In development (`ENV=development`), set `secure=False` to allow HTTP on localhost.

### Silent refresh flow

1. Frontend makes any API request.
2. FastAPI reads `access_token` cookie. If valid, proceed.
3. If access token is expired (401), the frontend Axios interceptor automatically calls `POST /auth/refresh`.
4. FastAPI reads `refresh_token` cookie, validates it, issues a new access token, sets a new cookie.
5. Axios retries the original request.
6. If refresh token is also expired, redirect to login.

### Axios interceptor pattern

```javascript
// api/client.js
axiosInstance.interceptors.response.use(
  response => response,
  async error => {
    const original = error.config;
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true;
      try {
        await axiosInstance.post('/auth/refresh');
        return axiosInstance(original);
      } catch {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);
```

### Auth endpoints

```
POST /auth/register     — creates user (role: user only, no role param accepted)
POST /auth/login        — sets access_token + refresh_token cookies
POST /auth/refresh      — rotates access_token using refresh_token cookie
POST /auth/logout       — clears both cookies (set max_age=0)
GET  /auth/me           — returns current user (reads role from DB, never JWT)
```

---

## Database Schema

Create all tables via Alembic migrations. Never alter the schema manually in production. Run `alembic upgrade head` on every deployment.

### Table: users
```sql
id            SERIAL PRIMARY KEY
email         VARCHAR(200) NOT NULL UNIQUE
password_hash VARCHAR(300) NOT NULL
role          VARCHAR(20) DEFAULT 'user'
is_active     BOOLEAN DEFAULT TRUE
created_at    TIMESTAMP DEFAULT NOW()
```

### Table: refresh_tokens
```sql
id            SERIAL PRIMARY KEY
user_id       INTEGER REFERENCES users(id) ON DELETE CASCADE
token_hash    VARCHAR(64) NOT NULL UNIQUE   -- SHA-256 of the raw refresh token
expires_at    TIMESTAMP NOT NULL
revoked       BOOLEAN DEFAULT FALSE
created_at    TIMESTAMP DEFAULT NOW()
```
Store a hash of the refresh token, not the raw value. On `POST /auth/logout`, set `revoked = TRUE`. On `POST /auth/refresh`, verify the hash exists, is not revoked, and is not expired — then rotate (revoke old, issue new).

### Table: categories
```sql
id            SERIAL PRIMARY KEY
name          VARCHAR(100) NOT NULL UNIQUE   -- slug, e.g. "hotel"
display_name  VARCHAR(100) NOT NULL          -- e.g. "Hotels"
created_at    TIMESTAMP DEFAULT NOW()
```

### Table: sources
```sql
id                        SERIAL PRIMARY KEY
category_id               INTEGER REFERENCES categories(id)
name                      VARCHAR(100) NOT NULL          -- e.g. "booking_com"
display_name              VARCHAR(100) NOT NULL          -- e.g. "Booking.com"
base_url                  VARCHAR(300) NOT NULL
heal_mode                 VARCHAR(20) DEFAULT 'AUTO'     -- 'AUTO' or 'MANUAL'
field_hints               JSONB                          -- real example values per field
is_active                 BOOLEAN DEFAULT TRUE
consecutive_failure_count INTEGER DEFAULT 0
created_at                TIMESTAMP DEFAULT NOW()
```

### Table: scrape_jobs
```sql
id                  UUID PRIMARY KEY DEFAULT gen_random_uuid()
user_id             INTEGER REFERENCES users(id)
category_id         INTEGER REFERENCES categories(id)
location            VARCHAR(200) NOT NULL
source_ids          INTEGER[]
failed_source_ids   INTEGER[]
parent_job_id       UUID REFERENCES scrape_jobs(id)   -- for retry jobs
status              VARCHAR(20) DEFAULT 'QUEUED'       -- QUEUED, RUNNING, DONE, FAILED
error_message       TEXT
celery_task_id      VARCHAR(200)
started_at          TIMESTAMP
completed_at        TIMESTAMP
created_at          TIMESTAMP DEFAULT NOW()
```

### Table: raw_results
```sql
id            UUID PRIMARY KEY DEFAULT gen_random_uuid()
job_id        UUID REFERENCES scrape_jobs(id)
source_id     INTEGER REFERENCES sources(id)
raw_data      JSONB NOT NULL
scraped_at    TIMESTAMP DEFAULT NOW()
```
This table is append-only. No UPDATE or DELETE ever. Every raw response is preserved here as an audit trail.

### Table: cleaned_results
```sql
id                  UUID PRIMARY KEY DEFAULT gen_random_uuid()
job_id              UUID REFERENCES scrape_jobs(id)
source_id           INTEGER REFERENCES sources(id)
category_id         INTEGER REFERENCES categories(id)
dedup_key           VARCHAR(64)                    -- SHA-256(lowercase(name)+lowercase(city))

-- Identity
name                VARCHAR(300)
brand               VARCHAR(200)
property_type       VARCHAR(100)
star_rating         SMALLINT

-- Location
address             TEXT
street_address      VARCHAR(300)
city                VARCHAR(100)
district            VARCHAR(100)
province            VARCHAR(100)
country             VARCHAR(100) DEFAULT 'Nepal'
latitude            NUMERIC(10, 7)
longitude           NUMERIC(10, 7)
neighbourhood       VARCHAR(200)
nearby_landmark     VARCHAR(300)

-- Contact
phone_primary       VARCHAR(50)
phone_secondary     VARCHAR(50)
email               VARCHAR(200)
website             VARCHAR(500)
facebook_url        VARCHAR(500)
instagram_handle    VARCHAR(200)
whatsapp_number     VARCHAR(50)

-- Pricing
price_min           NUMERIC(10, 2)
price_max           NUMERIC(10, 2)
currency            VARCHAR(10) DEFAULT 'NPR'
price_range_label   VARCHAR(20)
includes_breakfast  BOOLEAN
includes_taxes      BOOLEAN

-- Reviews
rating_overall      NUMERIC(4, 2)
rating_label        VARCHAR(50)
review_count        INTEGER
rating_cleanliness  NUMERIC(4, 2)
rating_location     NUMERIC(4, 2)
rating_facilities   NUMERIC(4, 2)
rating_service      NUMERIC(4, 2)
rating_value        NUMERIC(4, 2)

-- Facilities
amenities           JSONB
pets_allowed        BOOLEAN
breakfast_available BOOLEAN
checkin_time        VARCHAR(20)
checkout_time       VARCHAR(20)
cancellation_policy TEXT
free_cancellation   BOOLEAN

-- Media
thumbnail_url       TEXT
image_urls          JSONB
image_count         INTEGER

-- Content
description_short   TEXT
description_full    TEXT
highlights          JSONB
popular_with        JSONB
staff_languages     JSONB

-- Metadata
source_url          TEXT
source_listing_id   VARCHAR(200)
data_completeness   NUMERIC(5, 2)
is_edited           BOOLEAN DEFAULT FALSE
is_duplicate        BOOLEAN DEFAULT FALSE
status              VARCHAR(20) DEFAULT 'PENDING'   -- PENDING, APPROVED, REJECTED

created_at          TIMESTAMP DEFAULT NOW()
updated_at          TIMESTAMP DEFAULT NOW()
```

### Table: validated_results
**Do not duplicate all columns from `cleaned_results`.** Store only what differs or is added at approval time. Join to `cleaned_results` to read full record.
```sql
id                  UUID PRIMARY KEY DEFAULT gen_random_uuid()
cleaned_result_id   UUID NOT NULL REFERENCES cleaned_results(id) UNIQUE
pushed_by           INTEGER REFERENCES users(id)
pushed_at           TIMESTAMP DEFAULT NOW()
notes               TEXT          -- optional admin note at time of approval
```

### Table: scraper_selectors
```sql
id                  SERIAL PRIMARY KEY
source_id           INTEGER REFERENCES sources(id)
field_name          VARCHAR(100) NOT NULL
selector            TEXT NOT NULL
selector_type       VARCHAR(30) NOT NULL   -- 'testid', 'css', 'xpath', 'role', 'json_ld'
verified_at         TIMESTAMP
html_snapshot_hash  VARCHAR(64)            -- SHA-256 of page HTML when verified
is_active           BOOLEAN DEFAULT TRUE
UNIQUE(source_id, field_name)
```

### Table: selector_heal_log
```sql
id            SERIAL PRIMARY KEY
source_id     INTEGER REFERENCES sources(id)
field_name    VARCHAR(100)
old_selector  TEXT
new_selector  TEXT
trigger       VARCHAR(30)      -- 'initial_load', 'auto_reheal', 'manual_fix'
confidence    NUMERIC(4, 2)    -- 0.00–1.00, only for AUTO reheal attempts
status        VARCHAR(20) DEFAULT 'PENDING'   -- PENDING, RESOLVED, FAILED
html_snapshot TEXT             -- page HTML at time of failure, max 200KB
resolved_by   INTEGER REFERENCES users(id)
resolved_at   TIMESTAMP
healed_at     TIMESTAMP DEFAULT NOW()
```

### Table: geocoding_cache
```sql
id             SERIAL PRIMARY KEY
location_name  VARCHAR(200) NOT NULL UNIQUE
latitude       NUMERIC(10, 7)
longitude      NUMERIC(10, 7)
bounding_box   JSONB
cached_at      TIMESTAMP DEFAULT NOW()
```

### Table: city_bounding_boxes
```sql
id        SERIAL PRIMARY KEY
city_name VARCHAR(100) NOT NULL UNIQUE
min_lat   NUMERIC(10, 7)
min_lon   NUMERIC(10, 7)
max_lat   NUMERIC(10, 7)
max_lon   NUMERIC(10, 7)
```

Total: 12 tables.

---

## Database Indexes

Create all of these indexes in the Alembic migrations. Never leave a query-path column unindexed.

```sql
-- scrape_jobs: status polling and user history
CREATE INDEX idx_scrape_jobs_status       ON scrape_jobs(status);
CREATE INDEX idx_scrape_jobs_user_id      ON scrape_jobs(user_id);
CREATE INDEX idx_scrape_jobs_created_at   ON scrape_jobs(created_at DESC);

-- cleaned_results: admin table, filtering, sorting
CREATE INDEX idx_cleaned_results_job_id         ON cleaned_results(job_id);
CREATE INDEX idx_cleaned_results_status         ON cleaned_results(status);
CREATE INDEX idx_cleaned_results_category_id    ON cleaned_results(category_id);
CREATE INDEX idx_cleaned_results_data_complete  ON cleaned_results(data_completeness DESC);
CREATE INDEX idx_cleaned_results_dedup_key      ON cleaned_results(dedup_key);
CREATE INDEX idx_cleaned_results_city           ON cleaned_results(city);

-- raw_results: audit queries
CREATE INDEX idx_raw_results_job_id     ON raw_results(job_id);
CREATE INDEX idx_raw_results_source_id  ON raw_results(source_id);

-- selector_heal_log: admin panel filters
CREATE INDEX idx_heal_log_source_id  ON selector_heal_log(source_id);
CREATE INDEX idx_heal_log_status     ON selector_heal_log(status);

-- refresh_tokens: token validation
CREATE INDEX idx_refresh_tokens_user_id    ON refresh_tokens(user_id);
CREATE INDEX idx_refresh_tokens_token_hash ON refresh_tokens(token_hash);
```

---

## Seed Data

The seed script must read the admin password from the `ADMIN_PASSWORD` environment variable and refuse to run if it is not set.

### 30 Categories to seed
```
hotels, hostels, guesthouses, resorts, lodges, restaurants, cafes, bakeries,
pharmacies, hospitals, clinics, dental_clinics, banks, atms, petrol_stations,
supermarkets, schools, colleges, government_offices, police_stations,
fire_stations, embassies, trekking_agencies, travel_agencies, car_rentals,
bus_stations, temples, museums, parks, gyms
```

### City bounding boxes to seed
```
Kathmandu:  min_lat=27.62, min_lon=85.18, max_lat=27.82, max_lon=85.45
Pokhara:    min_lat=28.16, min_lon=83.92, max_lat=28.28, max_lon=84.06
Chitwan:    min_lat=27.52, min_lon=84.28, max_lat=27.75, max_lon=84.55
Biratnagar: min_lat=26.40, min_lon=87.20, max_lat=26.55, max_lon=87.35
Birgunj:    min_lat=26.94, min_lon=84.84, max_lat=27.05, max_lon=85.00
Butwal:     min_lat=27.64, min_lon=83.38, max_lat=27.76, max_lon=83.52
Dharan:     min_lat=26.76, min_lon=87.24, max_lat=26.85, max_lon=87.35
Hetauda:    min_lat=27.39, min_lon=84.86, max_lat=27.48, max_lon=84.98
Lalitpur:   min_lat=27.62, min_lon=85.28, max_lat=27.70, max_lon=85.36
Bhaktapur:  min_lat=27.66, min_lon=85.38, max_lat=27.72, max_lon=85.45
```

---

## How the Selector System Works

This is the most important system in the project. Read this carefully.

### Why selectors are in the database

If a selector is hardcoded in a Python file, a website redesign requires a code change and redeployment. With selectors in the database, the website can change its entire frontend and the fix is a single database row update — no code change, no redeployment.

### JSON-LD first pass (before any CSS selectors)

Before applying any selector from `scraper_selectors`, check every page for JSON-LD structured data in `<script type="application/ld+json">` tags. These are maintained by the site's SEO team and change far less often than visible HTML. Parse every JSON-LD block and extract: `name`, `address`, `telephone`, `geo` (lat/lon), `priceRange`, `starRating`, `aggregateRating`, `image`. Only fall back to CSS selectors for fields not found in JSON-LD.

### How a scraper uses selectors

1. At the start of each scrape, attempt JSON-LD extraction first.
2. Load all active selectors for this source from `scraper_selectors`.
3. For each field not already populated from JSON-LD, apply the selector.
4. If a selector returns nothing or throws an error, check the source's `heal_mode`.

### heal_mode AUTO — confidence threshold

Playwright/Camoufox reloads the live page and attempts to find the correct element by matching against `field_hints` in the sources table. Field hints are real example values (e.g., `{"name": "Hotel Himalaya", "rating_overall": "8.5"}`).

**Confidence scoring rules:**
- Score starts at 0.0
- +0.5 if the element has a `data-testid` attribute (unique and stable)
- +0.3 if it matches an ARIA role + accessible name
- +0.2 if structural XPath match
- -0.3 if the hint value appears in more than 3 elements on the page (ambiguous)

**Threshold:** Only accept and save the new selector if confidence ≥ 0.7. If below threshold, fall through to MANUAL behaviour and log the attempt with the computed confidence score.

Always save the HTML snapshot and the confidence score to `selector_heal_log.confidence` regardless of mode.

### heal_mode MANUAL

Downloads the current page HTML, saves it to `selector_heal_log` with `status = PENDING`. The admin panel shows this entry. The developer downloads the HTML, inspects it locally, finds the new selector, pastes it into the admin panel, which updates `scraper_selectors` and marks the log entry RESOLVED.

### Hash-based change detection

When a scraper successfully scrapes a page, save a SHA-256 hash of the page HTML to `scraper_selectors.html_snapshot_hash`. On every future scrape, before extracting data, compare the current page HTML hash to the saved hash. If they match, skip reheal and proceed. If they differ, run the reheal process regardless of whether selectors currently return data — the page may have changed in a way that degrades quality silently.

---

## How the Scraper Architecture Works

### Three types of scrapers

**Type 1 — Camoufox scrapers (protected JS-heavy sites)**
For: Booking.com, Agoda, TripAdvisor, OYO Rooms.
Uses Camoufox (Firefox-based anti-detect browser) via Crawlee's PlaywrightCrawler. Achieves 0% detection score on major fingerprinting tests. Handles Cloudflare, DataDome, and most anti-bot systems.

**Type 2 — Standard Playwright scrapers (moderate JS, lower protection)**
For: eSewa Hotels, Hostelworld, Zomato, Foodmandu.
Uses standard Playwright Chromium via Crawlee with user agent rotation and random delays.

**Type 3 — HTTP scrapers (static HTML, no JavaScript needed)**
For: NepalYP, Nepal Tourism Board, Nepal Police, NOC Nepal, DDA Nepal, Nepal Rastra Bank, TAAN, DOE Nepal, UGC Nepal, nepal.gov.np.
Uses `httpx` for HTTP and BeautifulSoup for parsing. No browser. 10x faster.

### BaseScraper responsibilities

Every scraper inherits from `BaseScraper`. It handles:
- Loading selectors from the `scraper_selectors` table at the start of each scrape
- JSON-LD first-pass extraction on every page
- Comparing page HTML hash against stored hash and triggering reheal if changed
- URL-encoding the `location` parameter before injecting into search URLs
- On selector failure: running AUTO reheal (if confidence ≥ 0.7) or saving HTML for MANUAL fix
- Anti-bot measures: random delays 1.5–3.5 seconds, user agent rotation, `navigator.webdriver` set to `undefined`, realistic viewport (1366×768), locale `en-US`
- CAPTCHA detection: after page load check for common CAPTCHA indicators. If detected, abort this source, record failure, increment `consecutive_failure_count`, continue with other sources
- Closing browser context in a `finally` block always
- Capturing full stack trace on failure and emitting a structured log event via structlog
- Reporting exceptions to Sentry with `source_id` and `job_id` as tags

### Orchestrator responsibilities

- Receives `job_id`, loads all parameters from the database
- Looks up which scraper class to use for each source via a registry dictionary
- Groups scrapers by base domain — scrapers for the same domain must not run concurrently
- Runs same-domain scrapers sequentially with a 2-second gap between them
- Runs different-domain groups in parallel with `asyncio.gather`
- Tracks which source IDs failed
- Returns `(results, failed_source_ids)` tuple

### Consecutive failure auto-disable

Every time a source scraper fails, increment `consecutive_failure_count`. Every time it succeeds, reset it to 0. When it reaches 3, set `is_active = False`. This is based on consecutive failures only — a source that fails 3 times over 6 months with 200 successes in between must not be disabled.

---

## Cleaning Pipeline

Run in this exact order after scraping:

1. **Save raw results** to `raw_results` table immediately — before any other processing. This is the audit trail.
2. **Normalise fields**: strip whitespace, format phone numbers, ensure website URLs start with `https://`, convert rating strings to float, store original casing.
3. **Within-job deduplication**: generate key from `SHA-256(lowercase(name) + lowercase(city))`. Skip if key already seen in this job batch.
4. **Cross-job deduplication**: query `cleaned_results` for existing rows with the same `dedup_key` and `category_id`. If found, set `is_duplicate = TRUE` and still insert (for audit), but mark it so the admin can filter duplicates out. Do not silently discard — the admin may want to see updated data.
5. **Validate fields**: if a field fails its pattern (phone must have digits, email must have `@`, rating must be 0–10), set that field to `NULL` rather than rejecting the whole record.
6. **Compute `data_completeness`** as percentage of 14 key fields that are non-NULL: `name, address, city, phone_primary, email, website, rating_overall, review_count, thumbnail_url, description_short, amenities, price_min, latitude, longitude`.
7. **Save to `cleaned_results`** with `status = PENDING`.

---

## Real-Time Job Status via Server-Sent Events (SSE)

Replace the polling approach with SSE. This eliminates unnecessary requests and delivers updates instantly.

### SSE endpoint

```
GET /jobs/{id}/stream
```

Returns a `StreamingResponse` with `Content-Type: text/event-stream`. Streams events until job status is `DONE` or `FAILED`, then sends a final event and closes.

### Event format

```
event: status
data: {"status": "RUNNING", "progress": 40, "message": "Scraping Booking.com..."}

event: status
data: {"status": "DONE", "result_count": 87}

event: error
data: {"status": "FAILED", "error": "Camoufox failed to bypass bot detection on Agoda"}
```

### FastAPI SSE implementation

```python
from fastapi.responses import StreamingResponse
import asyncio, json

@router.get("/jobs/{job_id}/stream")
async def stream_job_status(job_id: str, db: Session = Depends(get_db)):
    async def event_generator():
        while True:
            job = db.query(ScrapeJob).filter_by(id=job_id).first()
            payload = json.dumps({"status": job.status})
            yield f"event: status\ndata: {payload}\n\n"
            if job.status in ("DONE", "FAILED"):
                break
            await asyncio.sleep(2)
    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

### Frontend EventSource usage

```javascript
// hooks/useJobStream.js
export function useJobStream(jobId, onUpdate) {
  useEffect(() => {
    if (!jobId) return;
    const es = new EventSource(`/api/jobs/${jobId}/stream`, { withCredentials: true });
    es.addEventListener('status', e => onUpdate(JSON.parse(e.data)));
    es.onerror = () => es.close();
    return () => es.close();   // cleanup on unmount
  }, [jobId]);
}
```

Keep the old `GET /jobs/{id}/status` REST endpoint as a fallback for clients that do not support SSE.

---

## Pagination

All list endpoints must accept `page` and `page_size` query parameters and return a paginated envelope.

### Standard paginated response shape

```json
{
  "items": [...],
  "total": 1240,
  "page": 1,
  "page_size": 50,
  "pages": 25
}
```

### Paginated endpoints

| Endpoint | Default page_size | Max page_size |
|---|---|---|
| `GET /admin/results` | 50 | 200 |
| `GET /jobs/{id}/results` | 50 | 200 |
| `GET /admin/heal-log` | 50 | 200 |
| `GET /jobs` (user job history) | 20 | 100 |

### SQLAlchemy pagination pattern

```python
def paginate(query, page: int, page_size: int):
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return {"items": items, "total": total, "page": page,
            "page_size": page_size, "pages": -(-total // page_size)}
```

---

## Structured Logging

Use `structlog` for all logging. Never use `print()` or Python's `logging` module directly. All log output is JSON so Railway's log drain and any external log aggregator can parse it.

### Setup (main.py)

```python
import structlog

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer(),
    ]
)
logger = structlog.get_logger()
```

### Usage pattern

```python
logger.info("scraper.started", job_id=str(job_id), source="booking_com", location=location)
logger.error("scraper.failed", job_id=str(job_id), source="booking_com",
             exc_info=True, error=str(e))
logger.info("selector.healed", source_id=source_id, field="name",
            old_selector=old, new_selector=new, confidence=0.85)
```

### Key events to log

| Event key | When |
|---|---|
| `job.created` | POST /jobs succeeds |
| `job.queued` | Celery task dispatched |
| `job.started` | Celery task begins |
| `job.done` | Job completes successfully |
| `job.failed` | Job fails |
| `scraper.started` | Each source scraper begins |
| `scraper.captcha_detected` | CAPTCHA detected, aborting source |
| `scraper.failed` | Source scraper raises exception |
| `selector.healed` | AUTO reheal succeeded |
| `selector.heal_failed` | AUTO reheal confidence below threshold |
| `dedup.cross_job` | Cross-job duplicate detected |

---

## Error Tracking with Sentry

```python
# main.py
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.celery import CeleryIntegration

sentry_sdk.init(
    dsn=settings.SENTRY_DSN,
    integrations=[FastApiIntegration(), CeleryIntegration()],
    traces_sample_rate=0.1,       # 10% performance tracing
    environment=settings.ENV,     # "development" or "production"
    send_default_pii=False,       # never send user PII to Sentry
)
```

Add `SENTRY_DSN` to all environment configs. In development, set it to an empty string to disable. In production, set it to the real DSN from your Sentry project.

Tag every Sentry error with `job_id` and `source_name` so you can filter by scraper in the Sentry dashboard.

---

## Developer-Provided Selectors

Do not write any scraper until selectors are provided for that source. Leave unimplemented scrapers as stub classes with a comment: `# AWAITING SELECTORS FROM DEVELOPER`.

```python
{
    "source_name": "booking_com",
    "display_name": "Booking.com",
    "base_url": "https://www.booking.com",
    "category": "hotel",
    "heal_mode": "AUTO",
    "scraper_type": "camoufox",
    "field_hints": {
        "name": "Hotel Himalaya",
        "rating_overall": "8.5",
        "price_min": "3500",
        "address": "Kathmandu"
    },
    "selectors": {
        "name":           {"selector": "[data-testid='title']",                     "type": "testid"},
        "rating_overall": {"selector": "[data-testid='review-score-badge']",        "type": "testid"},
        "price_min":      {"selector": "[data-testid='price-and-discounted-price']","type": "testid"},
        "address":        {"selector": "[data-testid='address']",                   "type": "testid"},
        "thumbnail_url":  {"selector": "[data-testid='property-card-img']",         "type": "testid"}
    }
}
```

The seed script reads this configuration and populates both the `sources` table (with `field_hints`) and the `scraper_selectors` table.

---

## Fields to Extract

Extract as many of these as possible. Set fields to NULL when not available. Never skip a record because one field is missing.

- **Identity**: name, brand/chain, property_type, star_rating
- **Location**: address, street_address, city, district, province, country, latitude, longitude, neighbourhood, nearby_landmark
- **Contact**: phone_primary, phone_secondary, email, website, facebook_url, instagram_handle, whatsapp_number
- **Pricing**: price_min, price_max, currency, price_range_label, includes_breakfast, includes_taxes
- **Reviews**: rating_overall, rating_label, review_count, rating_cleanliness, rating_location, rating_facilities, rating_service, rating_value
- **Facilities**: amenities (JSONB array), pets_allowed, breakfast_available, checkin_time, checkout_time, cancellation_policy, free_cancellation
- **Media**: thumbnail_url, image_urls (JSONB array), image_count
- **Content**: description_short, description_full, highlights (JSONB), popular_with (JSONB), staff_languages (JSONB)
- **Metadata**: source_url, source_listing_id, data_completeness

**Data completeness key fields (14 total):** name, address, city, phone_primary, email, website, rating_overall, review_count, thumbnail_url, description_short, amenities, price_min, latitude, longitude.

---

## Source Mapping — Hotels First

Build scrapers in this order. Do not start the next source until the previous one is tested and working.

### Camoufox scrapers (scraper_type: camoufox)
- Booking.com — `booking.com/searchresults.html?ss={location}&ac_what=hotel`
- Agoda — `agoda.com/search?city={location}&type=hotel`
- TripAdvisor — `tripadvisor.com/Search?q={location}+hotels`
- OYO Rooms Nepal — `oyorooms.com/np/collection/{location}/`

### Standard Playwright scrapers (scraper_type: playwright)
- eSewa Hotels — `esewahotels.com/hotels/{location}`
- Hostelworld — `hostelworld.com/search?search_keywords={location}`

### HTTP scrapers (scraper_type: http)
- Nepal Tourism Board — `welcomenepal.com/accommodation`
- Hotel Association Nepal — `hotelassociationnepal.org` (member directory)
- Nepal Home Page — `nepalhomepage.com/travel/hotels`
- Hamrobazaar — hotels/guesthouses category

Always `urllib.parse.quote_plus(location)` before interpolating `{location}` into any URL.

---

## FastAPI Structure

```
backend/
  main.py               -- app, CORS, Sentry init, router includes
  config.py             -- all settings from env vars via pydantic-settings
  database.py           -- SQLAlchemy engine, session, base
  logging_config.py     -- structlog configuration
  models/               -- one file per table
  schemas/              -- Pydantic v2 request/response models
  routers/
    auth.py             -- POST /auth/register, /login, /refresh, /logout, GET /auth/me
    jobs.py             -- POST /jobs, GET /jobs, GET /jobs/{id}/status,
                          GET /jobs/{id}/stream (SSE), GET /jobs/{id}/results,
                          POST /jobs/{id}/retry
    results.py          -- PATCH /results/{id}, POST /results/{id}/approve (admin only)
    admin.py            -- GET /admin/results, POST /admin/results/bulk-approve,
                          GET /admin/heal-log, PATCH /admin/heal-log/{id}/resolve,
                          GET /admin/sources, PATCH /admin/sources/{id}/toggle
    categories.py       -- GET /categories, GET /categories/{id}/sources
  tasks/
    scrape_task.py      -- Celery task definition
  scrapers/
    base_scraper.py     -- abstract base with selector loading, reheal, anti-bot, logging
    inspector.py        -- selector inspection and reheal logic with confidence scoring
    orchestrator.py     -- groups and runs scrapers per job
    registry.py         -- dict mapping source names to scraper classes
    hotels/
      booking_com.py    -- camoufox scraper
      agoda.py          -- camoufox scraper (AWAITING SELECTORS)
      tripadvisor.py    -- camoufox scraper (AWAITING SELECTORS)
      oyo_rooms.py      -- camoufox scraper (AWAITING SELECTORS)
      esewa_hotels.py   -- playwright scraper (AWAITING SELECTORS)
      nepal_tourism_board.py  -- http scraper (AWAITING SELECTORS)
      hamrobazaar.py    -- http scraper (AWAITING SELECTORS)
  pipeline/
    cleaner.py          -- normalise, dedup (within-job + cross-job), validate
    validator.py        -- field-level validation rules
  services/
    auth_service.py     -- bcrypt, JWT, refresh token rotation
    job_service.py
    admin_service.py
    source_service.py
  tests/
    conftest.py         -- pytest fixtures, test DB setup
    test_auth.py
    test_jobs.py
    test_pipeline.py    -- cleaning, dedup, validation unit tests
    test_scrapers.py    -- mock-based scraper tests
    test_admin.py
```

---

## Celery Configuration

These settings are mandatory. Do not change them.

```python
task_acks_late = True              # task is only acknowledged after completion
worker_prefetch_multiplier = 1     # worker takes one task at a time
task_soft_time_limit = 300         # 5-minute soft timeout
task_time_limit = 360              # 6-minute hard kill
task_serializer = "json"
result_serializer = "json"
accept_content = ["json"]
```

Worker concurrency: `--concurrency=2` locally, `--concurrency=1` on Railway (only 1 browser instance fits safely with 1GB+ RAM on paid tier).

### Celery task pattern (mandatory)

```python
@celery_app.task(bind=True)
def scrape_task(self, job_id: str):
    db = SessionLocal()
    logger = structlog.get_logger().bind(job_id=job_id, task_id=self.request.id)
    try:
        update_job_status(db, job_id, "RUNNING")
        logger.info("job.started")
        results, failed_ids = orchestrator.run(db, job_id)
        store_failed_source_ids(db, job_id, failed_ids)
        pipeline.clean_and_store(db, job_id, results)
        update_job_status(db, job_id, "DONE")
        logger.info("job.done", result_count=len(results), failed_sources=len(failed_ids))
    except Exception as e:
        logger.error("job.failed", exc_info=True)
        sentry_sdk.capture_exception(e)
        update_job_status(db, job_id, "FAILED", error=str(e))
    finally:
        db.close()   # always runs — job is never stuck in RUNNING
```

---

## Security Checklist

Implement all of these before deployment.

- Passwords: bcrypt with `rounds=12`
- Access token: 15-minute expiry, `httpOnly` secure cookie
- Refresh token: 7-day expiry, `httpOnly` secure cookie, hash stored in DB, rotated on every use
- Role check: always load from DB on every protected request, never from JWT payload
- Register endpoint: ignores any `role` field in request body, always creates `role: user`
- Admin password: read from `ADMIN_PASSWORD` environment variable in seed script
- CORS: `http://localhost:5173` in development, deployed frontend domain only in production
- Rate limiting: `POST /jobs` limited to 10 requests per user per hour via `slowapi`
- Input validation: location validated as non-empty string, max 200 chars, stripped of leading/trailing whitespace; category validated against known slugs
- URL injection: always `urllib.parse.quote_plus(location)` before URL interpolation
- Credentials: all in environment variables, never in code or docker-compose.yml
- Celery task: receives only `job_id`, reads everything else from DB
- Sentry: `send_default_pii=False`

---

## Testing Strategy

Tests must be written for the pipeline and API. Never deploy to Railway without passing tests.

### Setup

```
pip install pytest pytest-asyncio httpx factory-boy
```

Use a separate test database. Set `DATABASE_URL` to a test PostgreSQL URL in `conftest.py`. Run migrations with `alembic upgrade head` before the test session.

### What to test

**Unit tests (no DB, no network)**
- `pipeline/cleaner.py`: normalisation functions, deduplication key generation, field validation rules, data_completeness calculation
- `scrapers/inspector.py`: confidence scoring logic for each selector type
- Auth service: JWT generation and verification, bcrypt hashing

**Integration tests (real test DB)**
- `POST /auth/register` → cannot pass `role` field
- `POST /auth/login` → sets `httpOnly` cookies
- `POST /auth/refresh` → rotates refresh token
- `POST /jobs` → creates job row, queues Celery task (mock the task)
- `GET /jobs/{id}/stream` → SSE stream returns correct events
- `PATCH /results/{id}` → optimistic lock (409 on stale `updated_at`)
- `POST /results/{id}/approve` → non-admin gets 403
- Pagination: verify `total`, `pages`, `items` count on all list endpoints

**Scraper tests (mock HTTP/browser)**
- Use `respx` to mock `httpx` responses for HTTP scrapers
- Use `unittest.mock` to mock Playwright/Camoufox for browser scrapers
- Verify JSON-LD extraction logic independently

### Running tests

```bash
# run all tests
pytest backend/tests/ -v

# run with coverage
pytest backend/tests/ --cov=backend --cov-report=term-missing
```

---

## Frontend Structure

```
frontend/src/
  components/
    UserView/
      CategorySelector.jsx
      LocationInput.jsx
      SourceSelector.jsx        -- multi-select, defaults to all if none selected
      ScrapeButton.jsx
      JobStatusDisplay.jsx      -- reads from SSE stream, shows Queued → Running → Done
      ResultsPreview.jsx
    AdminView/
      ResultsTable.jsx          -- TanStack Table with sorting, filtering, inline editing, pagination
      BrokenSelectorsPanel.jsx  -- PENDING heal log entries, download HTML, paste new selector
      SourceManager.jsx         -- enable/disable sources, show consecutive_failure_count
      HealLogViewer.jsx         -- full heal log with filters, confidence column
    Auth/
      LoginPage.jsx
      ProtectedRoute.jsx
  hooks/
    useJobStream.js             -- EventSource with cleanup on unmount
    useAuth.js                  -- reads /auth/me, handles 401 with redirect to login
    usePagination.js            -- shared pagination state hook
  api/
    client.js                   -- Axios with cookie credentials, refresh interceptor
    jobs.js
    results.js
    admin.js
    categories.js
```

### Axios client settings

```javascript
// api/client.js
const axiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
  withCredentials: true,   // sends cookies on every request — required for httpOnly auth
});
```

### Admin table rules

- When admin saves an inline edit: immediately `PATCH` the row, send `updated_at` for optimistic locking, set `is_edited = true`
- On 409 Conflict (stale `updated_at`): show error banner, refresh row from DB
- Filter `is_duplicate = true` rows into a separate "Duplicates" tab — don't mix with main results
- The Send/Approve endpoint reads from the DB row, never from frontend state
- Show `data_completeness` as a sortable percentage column
- Show `thumbnail_url` as a small image preview (50×50px)
- Show a "Duplicates" badge count in the table header

### CSRF protection note

Since cookies are `SameSite=Lax`, CSRF attacks that originate from cross-site navigation (forms, links) are blocked by default. For state-changing requests from JavaScript (Axios), browsers do not send cookies cross-origin because `withCredentials` requires the server's `Access-Control-Allow-Origin` to be an exact origin (not `*`). Ensure CORS is configured with explicit allowed origins, not wildcard.

---

## Docker Compose

Six services: postgres, redis, backend, worker, frontend, and a one-shot `migrator` service.

```yaml
services:

  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD", "pg_isready", "-U", "${POSTGRES_USER}"]
      interval: 5s
      timeout: 5s
      retries: 10

  redis:
    image: redis:7-alpine
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 10

  migrator:
    build: ./backend
    command: sh -c "alembic upgrade head && python seed.py"
    depends_on:
      postgres:
        condition: service_healthy
    env_file: .env
    restart: "no"   # run once and exit

  backend:
    build: ./backend
    command: uvicorn main:app --host 0.0.0.0 --port 8000
    depends_on:
      migrator:
        condition: service_completed_successfully
      redis:
        condition: service_healthy
    env_file: .env

  worker:
    build: ./backend
    command: celery -A tasks.scrape_task worker --loglevel=info --concurrency=2
    depends_on:
      migrator:
        condition: service_completed_successfully
      redis:
        condition: service_healthy
    shm_size: "1gb"   # required for Firefox/Camoufox
    env_file: .env

  frontend:
    build: ./frontend
    ports:
      - "5173:80"
    depends_on:
      - backend
```

All credentials in `.env`. Never commit `.env` to version control.

### Backend Dockerfile — browser dependencies

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright and Camoufox system dependencies
RUN pip install playwright camoufox "crawlee[playwright]"
RUN playwright install chromium
RUN playwright install-deps chromium
RUN camoufox fetch   # downloads the patched Firefox binary

COPY . .
```

---

## Deployment — Railway (Paid Hobby Tier Minimum)

**Do not use Railway free tier.** The free tier provides ~512MB RAM. A single Camoufox/Firefox instance uses 300–500MB, leaving insufficient headroom for the Python process. The worker will OOM crash under any real load. Use Railway Hobby tier ($5/month) which provides 8GB RAM shared across services.

### Services on Railway

| Service | Type | Notes |
|---|---|---|
| backend | Web Service | Runs uvicorn |
| worker | Background Worker | `shm_size` via env var workaround |
| frontend | Static Site or Web Service | Or deploy to Vercel/Netlify |
| PostgreSQL | Railway Plugin | Managed |
| Redis | Railway Plugin | Managed |

### Railway-specific settings

- Worker: set `CELERY_CONCURRENCY=1` (one browser instance per worker on Railway)
- Backend: configure start command as `alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port $PORT`
- All secrets in Railway environment variables dashboard — never in Dockerfile or source

### Railway shm workaround

Railway containers don't support `shm_size` from Docker Compose. Add this to your worker entrypoint script:

```bash
#!/bin/bash
# entrypoint-worker.sh
mount -t tmpfs -o size=1g tmpfs /dev/shm 2>/dev/null || true
exec celery -A tasks.scrape_task worker --loglevel=info --concurrency=$CELERY_CONCURRENCY
```

---

## Phase-by-Phase Build Order

Follow this order exactly. Do not start a phase until all tasks in the previous phase pass tests.

---

### PHASE 1 — Infrastructure Foundation

**Goal:** The full async job pipeline works with fake data before a single real scraper is written.

Tasks in order:
1. Create project folder structure for backend and frontend
2. Write `docker-compose.yml` with all six services, healthchecks, migrator service, and `shm_size` on worker
3. Write backend Dockerfile with playwright, camoufox, and crawlee installation
4. Write all Alembic migration files for all 12 tables including indexes
5. Verify all containers start, all healthchecks pass, FastAPI connects to PostgreSQL
6. Write the seed script (reads `ADMIN_PASSWORD` from env, seeds categories, city_bounding_boxes, placeholder sources)
7. Configure `structlog` and Sentry in `main.py`
8. Implement `User` and `RefreshToken` models and `AuthService`: bcrypt hashing, JWT generation (15min access, 7d refresh), JWT verification, refresh token rotation, token revocation
9. Implement auth routes: `POST /auth/register` (no role param), `POST /auth/login` (sets httpOnly cookies), `POST /auth/refresh` (rotates), `POST /auth/logout` (clears), `GET /auth/me`
10. Implement role-based dependency that loads role from DB — never from JWT payload
11. Write a fake Celery task `mock_scrape_task` that accepts `job_id`, sleeps 5 seconds, inserts 5 hardcoded fake `cleaned_results` rows, updates job status to DONE
12. Implement `POST /jobs`, `GET /jobs`, `GET /jobs/{id}/status`, `GET /jobs/{id}/stream` (SSE), `GET /jobs/{id}/results` (paginated)
13. Write auth and job integration tests
14. Test the complete pipeline: register user, login, POST /jobs, watch SSE stream, get paginated results

**Phase 1 is done when:** JWT cookie auth works, a job creates rows through QUEUED → RUNNING → DONE via the fake task, SSE stream delivers status events, results are paginated, and all integration tests pass.

---

### PHASE 2 — Scraper Core

**Goal:** The selector system, BaseScraper, Camoufox integration, and reheal logic all work. One real source (Booking.com) returns real data through the full pipeline.

Tasks in order:
1. Implement `inspector.py`: JSON-LD first pass, selector finding with testid → ARIA → XPath priority, confidence scoring (≥ 0.7 threshold), saves to `scraper_selectors`, logs to `selector_heal_log` with confidence score
2. Implement `BaseScraper`: selector loading, URL-encoding of location, hash comparison, reheal trigger, anti-bot settings, CAPTCHA detection, structlog events, Sentry tagging, failure snapshot saving
3. Implement `AutoRehealSystem`: hash comparison, inspector trigger, scraper_selectors update
4. Test Camoufox standalone: open browser, navigate to Booking.com, verify not blocked
5. Once developer provides selectors for Booking.com — implement `BookingComScraper` with JSON-LD first pass
6. Test `BookingComScraper` standalone (outside Celery): run directly, verify real hotel data for Kathmandu
7. Implement `ScraperOrchestrator`: registry dict, domain grouping, parallel/sequential execution, failure tracking
8. Implement cleaning pipeline: normalisation, within-job dedup, cross-job dedup with `is_duplicate` flag, validation, `data_completeness` scoring, raw_results save
9. Write pipeline unit tests (normalisation, dedup key generation, cross-job dedup logic, completeness scoring)
10. Replace `mock_scrape_task` with real orchestrator + pipeline
11. Run full end-to-end job with Booking.com

**Phase 2 is done when:** A real scrape job for Booking.com hotels in Kathmandu runs, returns real results, stores them in `cleaned_results` with all extracted fields, cross-job dedup works correctly, and pipeline unit tests pass.

---

### PHASE 3 — Frontend

**Goal:** Both user and admin views work against the real backend with real data from Booking.com.

Tasks in order:
1. Set up React + Vite, React Router, Axios instance with `withCredentials: true` and refresh interceptor
2. Implement auth context (`useAuth` hook reads `/auth/me`, handles 401 redirect), `LoginPage`, `ProtectedRoute`
3. Build user view: `CategorySelector`, `LocationInput`, `SourceSelector`, `ScrapeButton`
4. Implement `useJobStream` hook using EventSource with cleanup on unmount
5. Build `JobStatusDisplay` consuming SSE stream, showing Queued → Running → Done with progress indicator
6. Build `ResultsPreview` showing scraped data in a simple paginated table
7. Build admin `ResultsTable` using TanStack Table: sorting, filtering, inline editing, pagination controls, `data_completeness` sortable column, thumbnail preview, Duplicates tab
8. Implement optimistic locking: send `updated_at` with every PATCH, handle 409 by refreshing the row
9. Build Send button (individual) and bulk send
10. Build `BrokenSelectorsPanel`: shows PENDING heal log entries with confidence score, download HTML button, new selector input, type dropdown, Save & Retry button
11. Build `SourceManager`: toggle `is_active` per source, show `consecutive_failure_count`
12. Build `HealLogViewer`: filter by source, field, trigger type, status; show confidence column; HTML preview modal
13. Connect all components to real API, test full user flow and full admin flow

**Phase 3 is done when:** A user can log in (cookie auth, survives page refresh), trigger a Booking.com scrape, watch SSE status updates, see paginated results. An admin can log in, see the results table with duplicate flagging, edit a row, send it to `validated_results`.

---

### PHASE 4 — Scale and Harden

**Goal:** All hotel sources implemented, anti-bot hardening complete, system is production-ready.

Tasks in order:
1. Implement remaining hotel scrapers as developer provides selectors — in this order: Agoda, TripAdvisor, eSewa Hotels, OYO Rooms, Nepal Tourism Board, Hostelworld, Hamrobazaar
2. Implement `OverpassAPIClient` for Overpass/OpenStreetMap queries (plain HTTP, no browser, uses `city_bounding_boxes` table, falls back to Nominatim geocoding with 1 req/sec rate limit and caching in `geocoding_cache`)
3. Verify all scrapers work. Run a test job with all sources enabled.
4. Implement retry failed sources: `POST /jobs/{id}/retry` creates a new job with `parent_job_id` set and only the `failed_source_ids` from the original job
5. Anti-bot hardening review: verify Camoufox scrapers use random delays, same-domain concurrency control is working, CAPTCHA detection aborts gracefully, `structlog` emits `scraper.captcha_detected` event
6. Verify `slowapi` rate limiting blocks after 10 job submissions per user per hour
7. Deploy to Railway Hobby tier: set up all services, environment variables, run migrations, run seed script
8. Test the full system on the deployed version
9. Verify Sentry is receiving errors from the deployed environment
10. Write client handover documentation

**Phase 4 is done when:** All hotel sources are implemented, the deployed system works with real data, retry logic handles partial failures, Sentry receives errors, and all checklist items below are satisfied.

---

## Reference Sources

### Camoufox (anti-detect browser)
- Official docs: https://camoufox.com
- GitHub: https://github.com/daijro/camoufox
- Key fact: Camoufox wraps Playwright's API. Only the browser initialisation changes. Everything else (`page.locator`, `page.goto`, `page.evaluate`) is identical.

### Crawlee Python
- Official docs: https://crawlee.dev/python/
- GitHub: https://github.com/apify/crawlee-python
- Key fact: Crawlee handles request queuing, retries, concurrency scaling, and session rotation. Use `PlaywrightCrawler` with Camoufox for protected sites. Use `BeautifulSoupCrawler` for HTTP-only sites.

### FastAPI
- Official docs: https://fastapi.tiangolo.com
- SSE guide: https://fastapi.tiangolo.com/advanced/custom-response/#streamingresponse
- Dependency injection: https://fastapi.tiangolo.com/tutorial/dependencies/

### Celery
- Official docs: https://docs.celeryq.dev/en/stable/
- FastAPI + Celery: https://testdriven.io/blog/fastapi-and-celery/

### SQLAlchemy + Alembic
- SQLAlchemy 2.0 docs: https://docs.sqlalchemy.org/en/20/
- Alembic tutorial: https://alembic.sqlalchemy.org/en/latest/tutorial.html

### structlog
- Official docs: https://www.structlog.org/en/stable/

### Sentry
- FastAPI integration: https://docs.sentry.io/platforms/python/integrations/fastapi/
- Celery integration: https://docs.sentry.io/platforms/python/integrations/celery/

### TanStack Table v8
- Official docs: https://tanstack.com/table/v8/docs/introduction

### Overpass API (OpenStreetMap)
- Overpass API guide: https://wiki.openstreetmap.org/wiki/Overpass_API
- Nominatim geocoding: https://nominatim.org/release-docs/develop/api/Search/
- Key fact: Nominatim has a hard limit of 1 request per second. Always cache results in `geocoding_cache`.

### Railway deployment
- Railway docs: https://docs.railway.com
- Playwright in Docker: https://playwright.dev/python/docs/docker
- Key fact: always add `shm_size: "1gb"` to the worker service. Use Hobby tier minimum.

### Nepal-specific sources
- Nepal Government Portal: https://nepal.gov.np
- Nepal Oil Corporation: https://noc.org.np
- TAAN (Trekking Agencies): https://taan.org.np
- DDA Nepal (Pharmacies): https://dda.gov.np
- Nepal Police: https://nepalpolice.gov.np
- NepalYP: https://nepalyp.com
- eSewa Hotels: https://esewahotels.com
- Nepal Tourism Board: https://welcomenepal.com

---


## Appendix B — Exact Code Patterns and Operational Rules
 
This appendix provides code that must be used verbatim. Do not substitute patterns, do not use async SQLAlchemy, and do not deviate from the session lifecycle shown below. Every pattern here exists because the alternative has a known failure mode in this stack.
 
---
 
## B1 — requirements.txt (Pinned Versions)
 
```
# Web framework
fastapi==0.111.0
uvicorn[standard]==0.29.0
python-multipart==0.0.9
 
# Auth
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
 
# Database
sqlalchemy==2.0.30
alembic==1.13.1
psycopg2-binary==2.9.9
 
# Task queue
celery==5.3.6
redis==5.0.4
 
# HTTP scraping
httpx==0.27.0
beautifulsoup4==4.12.3
lxml==5.2.1
 
# Browser scraping
playwright==1.44.0
camoufox==0.4.1
crawlee[playwright]==0.1.2
 
# Logging and monitoring
structlog==24.1.0
sentry-sdk[fastapi,celery]==2.3.1
 
# Rate limiting
slowapi==0.1.9
 
# Config
pydantic-settings==2.2.1
 
# Testing
pytest==8.2.0
pytest-asyncio==0.23.6
httpx==0.27.0
respx==0.21.1
factory-boy==3.3.0
pytest-cov==5.0.0
```
 
---
 
## B2 — .env.example
 
```bash
# Copy to .env and fill in all values before running.
# Never commit .env to version control.
 
# App
ENV=development
SECRET_KEY=change-this-to-a-random-64-char-string-in-production
 
# Database
DATABASE_URL=postgresql://scraper:scraper_pass@postgres:5432/scraper_db
POSTGRES_DB=scraper_db
POSTGRES_USER=scraper
POSTGRES_PASSWORD=scraper_pass
 
# Redis / Celery
REDIS_URL=redis://redis:6379/0
CELERY_CONCURRENCY=2
 
# Admin seed
ADMIN_PASSWORD=
 
# Monitoring (leave empty in development to disable)
SENTRY_DSN=
 
# Frontend
VITE_API_URL=http://localhost:8000
VITE_ENV=development
 
# Railway-specific (only needed on Railway)
# PLAYWRIGHT_SHM_SIZE=1073741824
```
 
---
 
## B3 — Exact Pydantic Settings Model
 
File: `backend/config.py`
 
```python
from pydantic_settings import BaseSettings
from functools import lru_cache
 
class Settings(BaseSettings):
    ENV: str = "development"
    SECRET_KEY: str
    DATABASE_URL: str
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_CONCURRENCY: int = 2
    ADMIN_PASSWORD: str = ""
    SENTRY_DSN: str = ""
 
    # JWT
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"
 
    # CORS — set to deployed frontend URL in production
    FRONTEND_URL: str = "http://localhost:5173"
 
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
 
@lru_cache()
def get_settings() -> Settings:
    return Settings()
 
settings = get_settings()
```
 
`@lru_cache` means the `.env` file is read once at startup, not on every request.
 
---
 
## B4 — SQLAlchemy Patterns (SYNC, Not Async)
 
This project uses **synchronous SQLAlchemy** with Celery. Do not use `AsyncSession` or `async_sessionmaker` anywhere. Mixing async SQLAlchemy with Celery requires `asyncio.run()` wrappers that create subtle event loop lifecycle bugs. Sync is simpler, correct, and fast enough.
 
File: `backend/database.py`
 
```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from config import settings
 
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,      # reconnects if DB connection drops
    pool_size=10,
    max_overflow=20,
)
 
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
 
class Base(DeclarativeBase):
    pass
 
# FastAPI dependency — yields a session, always closes it
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```
 
### SQLAlchemy session lifecycle inside Celery tasks
 
This is a common source of silent bugs. Follow this pattern exactly.
 
```python
# tasks/scrape_task.py
from database import SessionLocal
 
@celery_app.task(bind=True)
def scrape_task(self, job_id: str):
    # Create a NEW session for this task — never share a session across threads
    db = SessionLocal()
    try:
        # All DB work happens inside this try block
        run_job(db, job_id)
        db.commit()   # explicit commit — autocommit is False
    except Exception as e:
        db.rollback()  # roll back any partial writes
        raise
    finally:
        db.close()     # ALWAYS close — even on exception, even on Celery retry
```
 
**Rules for Celery + SQLAlchemy:**
- Never use `next(get_db())` inside a Celery task — it is a FastAPI generator pattern and does not close properly outside a request context.
- Never reuse a session between tasks. Create a new `SessionLocal()` at the top of every task.
- Always call `db.close()` in a `finally` block. If you don't, connections leak and the pool exhausts under load.
- After `db.close()`, do not access any ORM objects that were loaded in that session — they will raise `DetachedInstanceError`. Load everything you need before closing.
---
 
## B5 — Exact Celery Setup
 
File: `backend/celery_app.py`
 
```python
from celery import Celery
from config import settings
 
celery_app = Celery(
    "scraper",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)
 
celery_app.conf.update(
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_soft_time_limit=300,
    task_time_limit=360,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Kathmandu",
    enable_utc=True,
)
```
 
Import `celery_app` into `scrape_task.py` — do not call `Celery(...)` more than once.
 
---
 
## B6 — Exact CORS Config
 
File: `backend/main.py`
 
```python
from fastapi.middleware.cors import CORSMiddleware
from config import settings
 
# In development: allow localhost:5173
# In production: allow only the deployed frontend domain
allowed_origins = (
    ["http://localhost:5173", "http://127.0.0.1:5173"]
    if settings.ENV == "development"
    else [settings.FRONTEND_URL]
)
 
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,   # required for httpOnly cookie auth
    allow_methods=["*"],
    allow_headers=["*"],
)
```
 
`allow_credentials=True` is mandatory — without it, the browser refuses to send cookies. When `allow_credentials=True`, `allow_origins` must be an explicit list, never `["*"]`.
 
---
 
## B7 — Exact Cookie Patterns
 
File: `backend/routers/auth.py`
 
```python
def set_auth_cookies(response: Response, access_token: str, refresh_token: str, settings):
    is_prod = settings.ENV == "production"
 
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=is_prod,        # False on localhost HTTP, True in production HTTPS
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=is_prod,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path="/auth/refresh",   # scope refresh token to only the refresh endpoint
    )
 
def clear_auth_cookies(response: Response):
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/auth/refresh")
```
 
Note: `path="/auth/refresh"` on the refresh token cookie means the browser only sends it to `/auth/refresh`, not to every API endpoint. This limits its exposure.
 
---
 
## B8 — Exact SSE Implementation with Clean Client-Disconnect Handling
 
The SSE generator must detect when the client disconnects and stop polling the database. Without this, every disconnected client leaves an infinite loop running in the server process.
 
File: `backend/routers/jobs.py`
 
```python
from fastapi import Request
from fastapi.responses import StreamingResponse
import asyncio, json
 
@router.get("/api/v1/jobs/{job_id}/stream")
async def stream_job_status(
    job_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    async def event_generator():
        try:
            while True:
                # Stop immediately if the client has closed the connection
                if await request.is_disconnected():
                    break
 
                job = db.query(ScrapeJob).filter_by(id=job_id).first()
                if not job:
                    yield f"event: error\ndata: {json.dumps({'error': 'job not found'})}\n\n"
                    break
 
                payload = {
                    "status": job.status,
                    "progress": getattr(job, "progress", 0),
                }
                yield f"event: status\ndata: {json.dumps(payload)}\n\n"
 
                if job.status in ("DONE", "FAILED"):
                    # Send final event, then close
                    break
 
                await asyncio.sleep(2)
        except asyncio.CancelledError:
            # Client disconnected mid-stream — exit cleanly, do not re-raise
            pass
 
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # disables Nginx buffering — required for SSE
        },
    )
```
 
`X-Accel-Buffering: no` is required if your deployment uses Nginx as a reverse proxy (Railway does). Without it, events are buffered and the client sees nothing until the buffer flushes.
 
---
 
## B9 — Camoufox Async Context Manager Pattern
 
Camoufox must always be used as an async context manager. If you do not close it in a `finally` block, Firefox processes accumulate and exhaust RAM.
 
```python
# scrapers/base_scraper.py
from camoufox.async_api import AsyncCamoufox
 
class BaseCamoufoxScraper:
    async def run(self, location: str) -> list[dict]:
        # AsyncCamoufox is an async context manager — always use `async with`
        async with AsyncCamoufox(
            headless=True,
            os="windows",        # spoof Windows OS fingerprint
            geoip=True,          # auto-set geolocation from exit IP
        ) as browser:
            context = await browser.new_context(
                viewport={"width": 1366, "height": 768},
                locale="en-US",
            )
            page = await context.new_page()
            try:
                return await self._scrape(page, location)
            except Exception as e:
                # Log and capture before re-raising
                logger.error("scraper.failed", source=self.source_name,
                             exc_info=True, error=str(e))
                sentry_sdk.capture_exception(e)
                raise
            finally:
                # Always close page and context — browser closes via `async with`
                await page.close()
                await context.close()
```
 
**Rules:**
- `async with AsyncCamoufox(...)` handles browser launch and teardown.
- Always close `page` and `context` in a `finally` block inside the `async with`.
- Never store a browser or context instance as a class attribute — create and destroy per scrape call.
- In the Celery task, call `asyncio.run(scraper.run(location))` since Celery workers are synchronous.
```python
# Inside Celery task — bridge sync Celery to async scraper
import asyncio
 
results = asyncio.run(orchestrator.run_async(db, job_id))
```
 
---
 
## B10 — HUMAN CHECKPOINT Markers
 
Insert these comments at every point that requires a human decision or external action before the AI can continue. The AI must stop and wait when it reaches a HUMAN CHECKPOINT.
 
```python
# ============================================================
# HUMAN CHECKPOINT — ACTION REQUIRED BEFORE CONTINUING
# ============================================================
# WHAT:   Booking.com selectors have not been provided yet.
# WHY:    This scraper cannot be implemented without real selectors
#         verified against the live site.
# DO:     1. Open https://www.booking.com/searchresults.html?ss=Kathmandu&ac_what=hotel
#         2. Inspect the HTML for each field in cleaned_results
#         3. Fill in the selectors dict in the seed script
#         4. Run the seed script to populate scraper_selectors
# THEN:   Uncomment the scraper implementation below and proceed.
# ============================================================
```
 
Use this pattern for: each unimplemented scraper, the Sentry DSN setup, the Railway deployment step, and the first real end-to-end test.
 
---
 
## B11 — DO NOT Rules (Extended)
 
Add these to the Hard Rules section. They are non-negotiable.
 
15. Do not use `async` SQLAlchemy anywhere in this project. Use synchronous `SessionLocal` only. See B4.
16. Do not use `print()` for logging. Use `structlog` logger exclusively.
17. Do not return unbounded lists from any endpoint. All list responses use the paginated envelope.
18. Do not share a SQLAlchemy session between a Celery task and a FastAPI request. Each creates its own.
19. Do not access ORM object attributes after `db.close()` — this raises `DetachedInstanceError`. Load all needed values before closing.
20. Do not run `camoufox fetch` inside the application. Run it once at Docker build time in the Dockerfile.
21. Do not catch bare `except Exception` without re-raising or recording to Sentry.
22. Do not set `allow_origins=["*"]` in CORS config — this breaks cookie auth entirely.
23. Do not hardcode `localhost` URLs in anything other than `.env.example` and dev-only config branches.
24. Do not call `asyncio.run()` inside an already-running event loop (i.e., inside a FastAPI route). Only call it inside Celery tasks.
---
 
## B12 — GitHub Actions CI
 
File: `.github/workflows/ci.yml`
 
```yaml
name: CI
 
on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]
 
jobs:
  test:
    runs-on: ubuntu-latest
 
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_DB: test_db
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
        ports: ["5432:5432"]
        options: >-
          --health-cmd pg_isready
          --health-interval 5s
          --health-retries 10
 
      redis:
        image: redis:7-alpine
        ports: ["6379:6379"]
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 5s
          --health-retries 10
 
    env:
      DATABASE_URL: postgresql://test:test@localhost:5432/test_db
      REDIS_URL: redis://localhost:6379/0
      SECRET_KEY: ci-test-secret-key-not-for-production
      ENV: test
      ADMIN_PASSWORD: ci-admin-password
 
    steps:
      - uses: actions/checkout@v4
 
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: "pip"
 
      - name: Install dependencies
        run: pip install -r backend/requirements.txt
 
      - name: Run migrations
        run: |
          cd backend
          alembic upgrade head
 
      - name: Run tests
        run: |
          cd backend
          pytest tests/ -v --cov=. --cov-report=term-missing --cov-fail-under=70
```
 
Never deploy to Railway without this CI passing. Add a Railway deploy hook that requires CI green.
 
---
 
## B13 — Health Endpoint
 
Every service needs a health endpoint. Railway uses it for zero-downtime deploys.
 
```python
# backend/routers/health.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from database import get_db
import redis as redis_lib
from config import settings
 
router = APIRouter()
 
@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    checks = {"status": "ok", "db": "ok", "redis": "ok"}
 
    # Check DB
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        checks["db"] = "error"
        checks["status"] = "degraded"
 
    # Check Redis
    try:
        r = redis_lib.from_url(settings.REDIS_URL)
        r.ping()
    except Exception:
        checks["redis"] = "error"
        checks["status"] = "degraded"
 
    return checks
```
 
Mount at `/health` (not under `/api/v1/`) so Railway's healthcheck probe doesn't need auth headers.
 
---
 
## B14 — API Versioning
 
All application routes are prefixed `/api/v1/`. The health endpoint is at `/health` (no version). Auth routes are at `/api/v1/auth/`.
 
```python
# backend/main.py
from routers import auth, jobs, results, admin, categories, health
 
app.include_router(health.router)                         # /health
app.include_router(auth.router,       prefix="/api/v1")  # /api/v1/auth/...
app.include_router(jobs.router,       prefix="/api/v1")  # /api/v1/jobs/...
app.include_router(results.router,    prefix="/api/v1")  # /api/v1/results/...
app.include_router(admin.router,      prefix="/api/v1")  # /api/v1/admin/...
app.include_router(categories.router, prefix="/api/v1")  # /api/v1/categories/...
```
 
Frontend Axios `baseURL` must be set to `VITE_API_URL + "/api/v1"` — not bare `VITE_API_URL`.
 
---
 
## B15 — Per-Domain Rate Limiting (Scraper)
 
The orchestrator must enforce that scrapers targeting the same base domain never run concurrently. This is separate from slowapi's per-user rate limiting on the POST /jobs endpoint.
 
```python
# scrapers/orchestrator.py
from urllib.parse import urlparse
from collections import defaultdict
import asyncio
 
class ScraperOrchestrator:
    async def run_async(self, db, job_id: str):
        job = db.query(ScrapeJob).filter_by(id=job_id).first()
        sources = db.query(Source).filter(Source.id.in_(job.source_ids)).all()
 
        # Group by base domain
        domain_groups: dict[str, list] = defaultdict(list)
        for source in sources:
            domain = urlparse(source.base_url).netloc  # e.g. "www.booking.com"
            domain_groups[domain].append(source)
 
        # Run each domain group sequentially; different domains run in parallel
        tasks = [
            self._run_domain_group(db, job_id, group)
            for group in domain_groups.values()
        ]
        group_results = await asyncio.gather(*tasks, return_exceptions=True)
 
        # Flatten results, collect failures
        all_results, failed_ids = [], []
        for group, result in zip(domain_groups.values(), group_results):
            if isinstance(result, Exception):
                failed_ids.extend(s.id for s in group)
            else:
                results, failures = result
                all_results.extend(results)
                failed_ids.extend(failures)
 
        return all_results, failed_ids
 
    async def _run_domain_group(self, db, job_id, sources):
        results, failed = [], []
        for source in sources:
            await asyncio.sleep(2)  # 2-second gap between same-domain requests
            try:
                scraper = registry[source.name]()
                data = await scraper.run(source, db)
                results.extend(data)
            except Exception:
                failed.append(source.id)
        return results, failed
```
 
---
 
## B16 — robots.txt Checking for HTTP Scrapers
 
HTTP scrapers (httpx/BeautifulSoup) must check `robots.txt` before scraping. Browser scrapers (Camoufox) are exempt — if you're using a browser it means the site already requires JS and robots.txt enforcement is at your discretion (still respect delays).
 
```python
# scrapers/robots_checker.py
import httpx
from urllib.robotparser import RobotFileParser
from urllib.parse import urljoin
import structlog
 
logger = structlog.get_logger()
_cache: dict[str, RobotFileParser] = {}
 
def can_fetch(base_url: str, user_agent: str = "*") -> bool:
    if base_url in _cache:
        rp = _cache[base_url]
    else:
        robots_url = urljoin(base_url, "/robots.txt")
        rp = RobotFileParser()
        rp.set_url(robots_url)
        try:
            rp.read()
            _cache[base_url] = rp
        except Exception:
            # If robots.txt is unreachable, assume allowed
            return True
 
    allowed = rp.can_fetch(user_agent, base_url)
    if not allowed:
        logger.warning("robots.disallowed", url=base_url, user_agent=user_agent)
    return allowed
```
 
Call `can_fetch(source.base_url)` at the top of every HTTP scraper's `run()` method. If it returns `False`, skip the source and log it — do not raise an exception.
 
---
 
## B17 — Data Retention Policy
 
Add a management command (not automatic) to purge old raw data. Never run this automatically — always require explicit admin action.
 
```python
# backend/management/purge_old_data.py
"""
Run manually: python -m management.purge_old_data --days=90
 
Purges raw_results rows older than N days. cleaned_results and validated_results
are never purged automatically — they are permanent business records.
"""
import argparse
from datetime import datetime, timedelta
from database import SessionLocal
from models.raw_results import RawResult
import structlog
 
logger = structlog.get_logger()
 
def purge(days: int):
    db = SessionLocal()
    cutoff = datetime.utcnow() - timedelta(days=days)
    try:
        count = db.query(RawResult).filter(RawResult.scraped_at < cutoff).count()
        db.query(RawResult).filter(RawResult.scraped_at < cutoff).delete()
        db.commit()
        logger.info("purge.complete", rows_deleted=count, cutoff=str(cutoff))
    finally:
        db.close()
```
 
Policy: `raw_results` older than 90 days may be purged. `cleaned_results` and `validated_results` are permanent. `selector_heal_log` older than 180 days may be purged.
 
---
 
## B18 — Frontend Error Boundaries
 
Wrap every major view section in an error boundary so a broken scraper result or malformed data field doesn't crash the entire admin panel.
 
```jsx
// components/ErrorBoundary.jsx
import { Component } from "react";
 
export class ErrorBoundary extends Component {
  state = { hasError: false, error: null };
 
  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }
 
  componentDidCatch(error, info) {
    // Log to console in dev; Sentry in prod
    console.error("ErrorBoundary caught:", error, info);
  }
 
  render() {
    if (this.state.hasError) {
      return (
        <div className="p-4 border border-red-300 rounded bg-red-50 text-red-800">
          <p className="font-semibold">Something went wrong in this panel.</p>
          <p className="text-sm mt-1">{this.state.error?.message}</p>
          <button
            className="mt-2 text-sm underline"
            onClick={() => this.setState({ hasError: false, error: null })}
          >
            Try again
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
```
 
Usage — wrap every admin panel section:
 
```jsx
<ErrorBoundary>
  <ResultsTable />
</ErrorBoundary>
<ErrorBoundary>
  <BrokenSelectorsPanel />
</ErrorBoundary>
```
 
---
 
## B19 — Exact TanStack Table v8 Patterns
 
TanStack Table v8 is headless — it provides state and handlers, not markup. You control all HTML.
 
```jsx
// components/AdminView/ResultsTable.jsx
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  flexRender,
} from "@tanstack/react-table";
import { useState } from "react";
 
const columns = [
  { accessorKey: "name",             header: "Name",        enableSorting: true },
  { accessorKey: "city",             header: "City",        enableSorting: true },
  { accessorKey: "rating_overall",   header: "Rating",      enableSorting: true },
  {
    accessorKey: "data_completeness",
    header: "Completeness",
    enableSorting: true,
    cell: ({ getValue }) => `${getValue()?.toFixed(1)}%`,
  },
  {
    accessorKey: "thumbnail_url",
    header: "Photo",
    enableSorting: false,
    cell: ({ getValue }) =>
      getValue() ? (
        <img src={getValue()} alt="thumbnail" className="w-12 h-12 object-cover rounded" />
      ) : "—",
  },
  {
    accessorKey: "is_duplicate",
    header: "Dup",
    enableSorting: false,
    cell: ({ getValue }) => getValue() ? <span className="text-orange-500">DUP</span> : null,
  },
];
 
export function ResultsTable({ data, pageCount, page, onPageChange }) {
  const [sorting, setSorting] = useState([]);
  const [columnFilters, setColumnFilters] = useState([]);
 
  const table = useReactTable({
    data,
    columns,
    pageCount,
    state: { sorting, columnFilters },
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    manualPagination: true,  // server-side pagination — do not set this to false
  });
 
  return (
    <div>
      <table className="w-full text-sm border-collapse">
        <thead>
          {table.getHeaderGroups().map(hg => (
            <tr key={hg.id}>
              {hg.headers.map(header => (
                <th
                  key={header.id}
                  className="text-left p-2 border-b font-semibold cursor-pointer select-none"
                  onClick={header.column.getToggleSortingHandler()}
                >
                  {flexRender(header.column.columnDef.header, header.getContext())}
                  {header.column.getIsSorted() === "asc" ? " ↑" : header.column.getIsSorted() === "desc" ? " ↓" : ""}
                </th>
              ))}
            </tr>
          ))}
        </thead>
        <tbody>
          {table.getRowModel().rows.map(row => (
            <tr key={row.id} className="hover:bg-gray-50 border-b">
              {row.getVisibleCells().map(cell => (
                <td key={cell.id} className="p-2">
                  {flexRender(cell.column.columnDef.cell, cell.getContext())}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
 
      {/* Pagination controls */}
      <div className="flex gap-2 mt-3 items-center text-sm">
        <button onClick={() => onPageChange(page - 1)} disabled={page === 1}>← Prev</button>
        <span>Page {page} of {pageCount}</span>
        <button onClick={() => onPageChange(page + 1)} disabled={page === pageCount}>Next →</button>
      </div>
    </div>
  );
}
```
 
Key rule: always set `manualPagination: true` — pagination is server-side. Never let TanStack Table slice the data locally.
 
---
 
## B20 — Exact Axios Interceptor Pattern (Complete)
 
```javascript
// frontend/src/api/client.js
import axios from "axios";
 
const api = axios.create({
  baseURL: `${import.meta.env.VITE_API_URL}/api/v1`,
  withCredentials: true,   // sends httpOnly cookies on every request
  timeout: 30000,
});
 
let isRefreshing = false;
let failedQueue = [];        // requests that failed while a refresh was in progress
 
function processQueue(error) {
  failedQueue.forEach(prom => error ? prom.reject(error) : prom.resolve());
  failedQueue = [];
}
 
api.interceptors.response.use(
  response => response,
  async error => {
    const original = error.config;
 
    if (error.response?.status === 401 && !original._retry) {
      if (isRefreshing) {
        // Another refresh is already in-flight — queue this request
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        }).then(() => api(original)).catch(err => Promise.reject(err));
      }
 
      original._retry = true;
      isRefreshing = true;
 
      try {
        await api.post("/auth/refresh");   // sets new access_token cookie
        processQueue(null);
        return api(original);              // retry the original request
      } catch (refreshError) {
        processQueue(refreshError);
        window.location.href = "/login";   // refresh token also expired
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }
 
    return Promise.reject(error);
  }
);
 
export default api;
```
 
The `failedQueue` pattern is essential: if 3 requests arrive simultaneously while the access token is expired, without it all 3 will try to call `/auth/refresh` in parallel, causing race conditions and cookie conflicts. The queue holds them until one refresh completes, then retries all of them.
 
---
 
## B21 — Frontend package.json Dependencies
 
```json
{
  "name": "scraper-portal-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-router-dom": "^6.23.1",
    "axios": "^1.7.2",
    "@tanstack/react-table": "^8.17.3"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.3.0",
    "vite": "^5.2.11",
    "tailwindcss": "^3.4.3",
    "autoprefixer": "^10.4.19",
    "postcss": "^8.4.38"
  }
}
```
 
---
 



## Checklist Before Handing Over to Client

### Database & Infrastructure
- [ ] All 12 database tables exist, are properly indexed, and are seeded
- [ ] Alembic migrations run cleanly on a fresh database
- [ ] All five Docker services start healthy; migrator runs and exits cleanly
- [ ] `shm_size` workaround applied for Railway worker

### Authentication
- [ ] `POST /auth/register` cannot accept a `role` field
- [ ] Login sets `httpOnly` `SameSite=Lax` cookies (access + refresh)
- [ ] Silent refresh works: page refresh does not log user out
- [ ] Refresh token rotation: old token revoked when new one issued
- [ ] Logout clears both cookies and revokes refresh token in DB
- [ ] Role is always read from DB, never from JWT payload

### Scraping Pipeline
- [ ] Full scrape job lifecycle: submit → SSE stream → QUEUED → RUNNING → DONE → results visible
- [ ] At least one Camoufox scraper (Booking.com) returns real data
- [ ] JSON-LD extraction is attempted before CSS selectors on every page
- [ ] `location` is URL-encoded before injection into scraper URLs
- [ ] Cross-job deduplication works: running same job twice flags duplicates, not silent discard
- [ ] Within-job deduplication works
- [ ] `raw_results` is append-only and never modified

### Selector Reheal
- [ ] AUTO reheal: confidence scoring is working; only saves selector if ≥ 0.7
- [ ] MANUAL reheal: HTML snapshot saved, admin panel shows PENDING entry
- [ ] Hash-based change detection triggers reheal when page HTML changes
- [ ] `selector_heal_log.confidence` is populated for all AUTO attempts

### Admin Panel
- [ ] Paginated results table (50 per page default)
- [ ] `data_completeness` column is sortable
- [ ] Duplicate records shown in separate tab with `is_duplicate` flag
- [ ] Inline edit triggers optimistic lock (409 on stale `updated_at`)
- [ ] Admin can send individual and bulk records to `validated_results`
- [ ] `validated_results` stores only a FK reference to `cleaned_results`, not full duplicate columns
- [ ] BrokenSelectorsPanel shows confidence score per PENDING entry

### Observability
- [ ] `structlog` JSON logs emitted to stdout on all key events
- [ ] Sentry receiving errors from deployed environment (verify in Sentry dashboard)
- [ ] `send_default_pii=False` confirmed in Sentry config

### Security
- [ ] Passwords bcrypt with `rounds=12`
- [ ] No credentials hardcoded anywhere (code, docker-compose.yml, Dockerfile)
- [ ] CORS restricted to correct frontend domain in production (not wildcard)
- [ ] Rate limiting blocks after 10 job submissions per user per hour
- [ ] Admin password read from `ADMIN_PASSWORD` env var

### Testing
- [ ] Pipeline unit tests pass (normalisation, dedup, validation, completeness)
- [ ] Auth integration tests pass
- [ ] Job lifecycle integration tests pass
- [ ] Pagination integration tests pass
- [ ] `pytest` runs with no failures on CI before every deployment

### Deployment
- [ ] Railway Hobby tier (not free tier)
- [ ] All secrets in Railway environment variables dashboard
- [ ] Migrations run automatically before uvicorn starts
- [ ] Seed script ran on first deployment
- [ ] All Railway services show healthy status

---

## What Success Looks Like

A client using the portal should be able to:

1. Select "Hotels" and type "Kathmandu"
2. Click Scrape and watch real-time status via SSE — no polling, instant updates
3. See results appear once the job completes
4. Refresh the page and still be logged in (cookie auth survives refresh)
5. An admin logs in, sees a paginated table of hotels with thumbnails, ratings, prices, amenities
6. Admin sees a Duplicates tab showing records that appeared in previous runs
7. Admin edits a phone number that was scraped incorrectly
8. Admin clicks Send — the corrected record appears in `validated_results` (referenced, not duplicated)
9. Six months later, Booking.com updates their HTML — the system automatically fixes itself if confidence ≥ 0.7, or queues a PENDING entry in the heal log for manual fix
10. The developer checks Sentry and sees the heal attempt logged with its confidence score

That is the bar. Build to that bar.
