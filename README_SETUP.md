# Quick Setup Guide - Fresh Laptop

## 1. Install Software (20 minutes)

### Git
- Download: https://git-scm.com/download/win
- Install with defaults

### Docker Desktop  
- Download: https://www.docker.com/products/docker-desktop/
- Install and restart computer
- After restart: Settings → Resources → Memory → **8 GB**

### Python 3.11
- Download: https://www.python.org/downloads/
- **CHECK "Add Python to PATH"** during install

## 2. Get the Code (2 minutes)

```powershell
cd Desktop
git clone https://github.com/ujju1124/Gen_Scraper.git
cd Gen_Scraper
```

## 3. Setup for Test (3 minutes)

```powershell
# Install Python packages
pip install requests psycopg2-binary

# Disable other sources (only test Booking.com)
docker-compose up -d
timeout /t 30
docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c "UPDATE sources SET is_active = false WHERE name != 'booking_com';"
docker-compose restart worker
```

## 4. Run Test (5 minutes)

Create `test.py`:
```python
import requests, time

session = requests.Session()
session.post("http://localhost:8000/api/v1/auth/login", 
             json={"email": "admin@example.com", "password": "admin123"})

r = session.post("http://localhost:8000/api/v1/jobs/",
                 json={"location": "Kathmandu", "source_names": ["booking_com"], 
                       "max_results": 5, "category_id": 1})
job_id = r.json()["id"]
print(f"Job: {job_id}")

for i in range(60):
    time.sleep(5)
    status = session.get(f"http://localhost:8000/api/v1/jobs/{job_id}/status").json()["status"]
    if i % 6 == 0: print(f"[{i*5}s] {status}")
    if status in ["COMPLETED", "FAILED"]: break

print(f"\nDone! Check results:")
print(f'docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c "SELECT raw_data->>\'name\', raw_data->>\'price_min\', raw_data->>\'star_rating\' FROM raw_results r JOIN sources s ON r.source_id = s.id WHERE s.name = \'booking_com\' ORDER BY r.scraped_at DESC LIMIT 5;"')
```

Run: `python test.py`

## 5. Check Results

```powershell
docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c "SELECT raw_data->>'name' as name, raw_data->>'price_min' as price, raw_data->>'star_rating' as stars FROM raw_results r JOIN sources s ON r.source_id = s.id WHERE s.name = 'booking_com' ORDER BY r.scraped_at DESC LIMIT 5;"
```

## Success = Prices and Stars Populated! ✅

If you see prices and star ratings, the fix works!
