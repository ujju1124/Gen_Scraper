"""
Bulk data collection script — creates scraping jobs for all cities and categories.

Run with:
    docker exec gen_scraper-backend-1 python scripts/bulk_collect.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
import time
from database import SessionLocal
from models.category import Category
from models.source import Source

BASE_URL = "http://localhost:8000/api/v1"

# Define all jobs to create
# Format: (category_name, source_name, city, max_results)
JOBS = [
    # Kathmandu — full coverage with active sources
    ("hotels", "hostelworld", "Kathmandu", 200),
    ("hotels", "directoryofnepal_hotels", "Kathmandu", 200),
    ("hotels", "google_maps", "Kathmandu", 100),
    
    ("restaurants", "directoryofnepal_restaurants", "Kathmandu", 200),
    ("restaurants", "google_maps", "Kathmandu", 100),
    
    ("pharmacies", "directoryofnepal_pharmacies", "Kathmandu", 100),
    ("pharmacies", "google_maps", "Kathmandu", 100),
    
    ("hospitals", "google_maps", "Kathmandu", 100),
    ("clinics", "nepalyp_clinics", "Kathmandu", 100),
    ("clinics", "google_maps", "Kathmandu", 100),
    
    ("banks", "nepalyp_banks", "Kathmandu", 100),
    ("banks", "google_maps", "Kathmandu", 50),
    
    ("schools", "nepalyp_schools", "Kathmandu", 100),
    ("colleges", "nepalyp_colleges", "Kathmandu", 100),
    
    ("bakeries", "nepalyp_bakers", "Kathmandu", 100),
    ("bakeries", "google_maps", "Kathmandu", 50),
    
    ("travel_agencies", "nepalyp_travel_agents", "Kathmandu", 100),
    ("travel_agencies", "nepalyp_tour_operators", "Kathmandu", 100),
    
    ("car_rentals", "nepalyp_car_rental", "Kathmandu", 100),
    ("petrol_stations", "nepalyp_petrol_stations", "Kathmandu", 100),
    
    ("supermarkets", "nepalyp_shopping_centres", "Kathmandu", 100),
    ("resorts", "nepalyp_resorts", "Kathmandu", 100),
    ("hostels", "nepalyp_homestays", "Kathmandu", 100),
    
    # Pokhara — major tourist city
    ("hotels", "hostelworld", "Pokhara", 200),
    ("hotels", "directoryofnepal_hotels", "Pokhara", 200),
    ("hotels", "google_maps", "Pokhara", 100),
    
    ("restaurants", "directoryofnepal_restaurants", "Pokhara", 150),
    ("restaurants", "google_maps", "Pokhara", 100),
    
    ("pharmacies", "directoryofnepal_pharmacies", "Pokhara", 50),
    ("hospitals", "google_maps", "Pokhara", 50),
    ("banks", "nepalyp_banks", "Pokhara", 50),
    ("travel_agencies", "nepalyp_travel_agents", "Pokhara", 50),
    
    # Biratnagar — second largest city
    ("hotels", "directoryofnepal_hotels", "Biratnagar", 100),
    ("hotels", "google_maps", "Biratnagar", 50),
    ("restaurants", "directoryofnepal_restaurants", "Biratnagar", 100),
    ("restaurants", "google_maps", "Biratnagar", 50),
    ("hospitals", "google_maps", "Biratnagar", 50),
    ("banks", "nepalyp_banks", "Biratnagar", 50),
    
    # Birgunj — border city
    ("hotels", "directoryofnepal_hotels", "Birgunj", 100),
    ("hotels", "google_maps", "Birgunj", 50),
    ("restaurants", "directoryofnepal_restaurants", "Birgunj", 100),
    ("hospitals", "google_maps", "Birgunj", 50),
    
    # Butwal — growing city
    ("hotels", "directoryofnepal_hotels", "Butwal", 100),
    ("restaurants", "directoryofnepal_restaurants", "Butwal", 100),
    ("hospitals", "google_maps", "Butwal", 50),
    
    # Dharan — eastern city
    ("hotels", "directoryofnepal_hotels", "Dharan", 100),
    ("restaurants", "directoryofnepal_restaurants", "Dharan", 100),
    
    # Lalitpur — part of Kathmandu Valley
    ("hotels", "directoryofnepal_hotels", "Lalitpur", 100),
    ("restaurants", "directoryofnepal_restaurants", "Lalitpur", 100),
    ("restaurants", "google_maps", "Lalitpur", 50),
    
    # Bhaktapur — historic city
    ("hotels", "directoryofnepal_hotels", "Bhaktapur", 100),
    ("restaurants", "directoryofnepal_restaurants", "Bhaktapur", 100),
    ("restaurants", "google_maps", "Bhaktapur", 50),
    
    # Additional NepalYP categories for Kathmandu
    ("government_offices", "nepalyp_insurance", "Kathmandu", 50),
    ("car_rentals", "nepalyp_motorcycle_dealers", "Kathmandu", 50),
    ("temples", "nepalyp_tourist_attractions", "Kathmandu", 100),
    ("bus_stations", "nepalyp_courier", "Kathmandu", 50),
]


def get_category_id(name: str) -> int:
    """Get category ID by name."""
    db = SessionLocal()
    try:
        cat = db.query(Category).filter(Category.name == name).first()
        return cat.id if cat else None
    finally:
        db.close()


def get_source_id(name: str) -> int:
    """Get source ID by name."""
    db = SessionLocal()
    try:
        src = db.query(Source).filter(Source.name == name).first()
        return src.id if src else None
    finally:
        db.close()


def login() -> requests.Session:
    """Login and return authenticated session."""
    print("🔐 Logging in...")
    session = requests.Session()
    
    response = session.post(
        f"{BASE_URL}/auth/login",
        json={"email": "admin@example.com", "password": "admin123"}
    )
    
    if response.status_code != 200:
        print(f"❌ Login failed: {response.status_code} - {response.text}")
        sys.exit(1)
    
    print("✅ Login successful")
    return session


def create_job(session: requests.Session, category_id: int, source_id: int, city: str, max_results: int) -> tuple[bool, str]:
    """Create a single scrape job."""
    response = session.post(
        f"{BASE_URL}/jobs/",  # Note the trailing slash
        json={
            "category_id": category_id,
            "location": city,
            "source_ids": [source_id],
            "max_results": max_results
        }
    )
    
    # Accept both 200 and 201 as success
    success = response.status_code in [200, 201]
    return success, response.text if not success else ""


def main():
    """Main execution function."""
    print("=" * 80)
    print("🚀 BULK DATA COLLECTION SCRIPT")
    print("=" * 80)
    print()
    
    # Login
    session = login()
    print()
    
    # Create jobs
    print(f"📋 Creating {len(JOBS)} scrape jobs...")
    print()
    
    created = 0
    skipped = 0
    failed = 0
    
    for category_name, source_name, city, max_results in JOBS:
        # Get IDs
        category_id = get_category_id(category_name)
        source_id = get_source_id(source_name)
        
        # Validate
        if not category_id:
            print(f"⚠️  SKIP: Category '{category_name}' not found in DB")
            skipped += 1
            continue
        
        if not source_id:
            print(f"⚠️  SKIP: Source '{source_name}' not found in DB")
            skipped += 1
            continue
        
        # Create job
        success, error_msg = create_job(session, category_id, source_id, city, max_results)
        
        if success:
            print(f"✅ Created: {category_name:20s} / {source_name:30s} / {city:15s} / limit={max_results}")
            created += 1
        else:
            print(f"❌ Failed:  {category_name:20s} / {source_name:30s} / {city:15s}")
            if error_msg and failed == 0:  # Only show first error
                print(f"   Error: {error_msg[:200]}")
            failed += 1
        
        # Small delay to avoid overwhelming the API
        time.sleep(0.5)
    
    # Summary
    print()
    print("=" * 80)
    print("📊 SUMMARY")
    print("=" * 80)
    print(f"✅ Created: {created} jobs")
    print(f"⚠️  Skipped: {skipped} jobs (missing category/source)")
    print(f"❌ Failed:  {failed} jobs")
    print()
    
    if created > 0:
        print("🎉 Jobs are now queued — Celery worker will process them automatically!")
        print()
        print("📈 Monitor progress with:")
        print()
        print("  # Check job status")
        print("  docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c \\")
        print("    \"SELECT status, COUNT(*) FROM scrape_jobs GROUP BY status;\"")
        print()
        print("  # Check total records collected")
        print("  docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c \\")
        print("    \"SELECT COUNT(*) as total FROM cleaned_results;\"")
        print()
        print("  # Check records by city")
        print("  docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c \\")
        print("    \"SELECT city, COUNT(*) as records FROM cleaned_results GROUP BY city ORDER BY COUNT(*) DESC LIMIT 10;\"")
        print()
        print("  # Check worker logs")
        print("  docker logs gen_scraper-worker-1 --tail 50 -f")
        print()
    
    print("=" * 80)


if __name__ == "__main__":
    main()
