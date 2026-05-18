"""
City Expansion Script - Create targeted jobs for cities with low coverage

This script creates scrape jobs for NepalYP sources across multiple cities
to expand geographic coverage beyond Kathmandu and Pokhara.

Target cities: Biratnagar, Birgunj, Butwal, Hetauda
Categories: Hotels, Restaurants, Hospitals, Pharmacies, Banks
"""

import requests
import time
from database import SessionLocal
from models.category import Category
from models.source import Source

BASE_URL = "http://localhost:8000/api/v1"

# Login to get authentication cookies
print("Logging in...")
login = requests.post(
    f"{BASE_URL}/auth/login",
    json={"email": "admin@example.com", "password": "admin123"}
)

if login.status_code != 200:
    print(f"❌ Login failed: {login.status_code}")
    print(login.text)
    exit(1)

cookies = login.cookies
print("✅ Login successful")

# Initialize database session
db = SessionLocal()

# Define jobs: (category_slug, source_name, city, max_results)
JOBS = [
    # Hotels
    ("hotels", "nepalyp", "Biratnagar", 100),
    ("hotels", "nepalyp", "Birgunj", 100),
    ("hotels", "nepalyp", "Butwal", 100),
    ("hotels", "nepalyp", "Hetauda", 100),
    
    # Restaurants
    ("restaurants", "nepalyp_restaurants", "Biratnagar", 100),
    ("restaurants", "nepalyp_restaurants", "Birgunj", 100),
    ("restaurants", "nepalyp_restaurants", "Butwal", 100),
    
    # Hospitals
    ("hospitals", "nepalyp_hospitals", "Pokhara", 100),
    ("hospitals", "nepalyp_hospitals", "Biratnagar", 100),
    
    # Pharmacies
    ("pharmacies", "nepalyp_pharmacies", "Pokhara", 100),
    
    # Banks
    ("banks", "nepalyp_banks", "Pokhara", 100),
    ("banks", "nepalyp_banks", "Biratnagar", 100),
]

print(f"\nCreating {len(JOBS)} jobs...")
print("=" * 80)

created = 0
skipped = 0
failed = 0

for cat_slug, src_name, city, limit in JOBS:
    # Look up category
    cat = db.query(Category).filter(Category.name == cat_slug).first()
    if not cat:
        print(f"⚠️  SKIP: Category '{cat_slug}' not found")
        skipped += 1
        continue
    
    # Look up source
    src = db.query(Source).filter(Source.name == src_name).first()
    if not src:
        print(f"⚠️  SKIP: Source '{src_name}' not found")
        skipped += 1
        continue
    
    # Create job
    try:
        response = requests.post(
            f"{BASE_URL}/jobs",
            cookies=cookies,
            json={
                "category_id": cat.id,
                "location": city,
                "source_ids": [src.id],
                "max_results": limit
            }
        )
        
        if response.status_code in [200, 201]:
            job_data = response.json()
            job_id = job_data.get("id", "unknown")
            status = "✅"
            created += 1
            print(f"{status} {cat_slug:15} | {src_name:25} | {city:12} | limit={limit:3} | job_id={job_id[:8]}...")
        else:
            status = "❌"
            failed += 1
            print(f"{status} {cat_slug:15} | {src_name:25} | {city:12} | limit={limit:3} | HTTP {response.status_code}")
            print(f"   Error: {response.text[:100]}")
    
    except Exception as e:
        status = "❌"
        failed += 1
        print(f"{status} {cat_slug:15} | {src_name:25} | {city:12} | limit={limit:3} | Error: {str(e)[:50]}")
    
    # Rate limiting: 1 second between requests
    time.sleep(1)

# Close database session
db.close()

# Print summary
print("=" * 80)
print(f"\n📊 Summary:")
print(f"   ✅ Created: {created} jobs")
print(f"   ⚠️  Skipped: {skipped} jobs (category/source not found)")
print(f"   ❌ Failed:  {failed} jobs")
print(f"   📝 Total:   {len(JOBS)} jobs")

if created > 0:
    print(f"\n🚀 Worker will process {created} jobs automatically")
    print(f"   Expected duration: 2-3 hours (NepalYP only, no browser automation)")
    print(f"\n📈 Monitor progress:")
    print(f"   docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c \\")
    print(f"     \"SELECT status, COUNT(*) FROM scrape_jobs WHERE status != 'CANCELLED' GROUP BY status;\"")
else:
    print(f"\n⚠️  No jobs created. Check category and source names.")
