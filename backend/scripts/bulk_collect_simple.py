"""
Simple bulk data collection script — creates scraping jobs for all active sources.

Run with:
    docker exec gen_scraper-backend-1 python scripts/bulk_collect_simple.py
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

# Cities to scrape
CITIES = ["Kathmandu", "Pokhara", "Biratnagar", "Birgunj", "Butwal", "Dharan", "Lalitpur", "Bhaktapur"]

# Category to source mapping with limits
CATEGORY_SOURCE_MAP = {
    "hotels": [
        ("hostelworld", 200),
        ("directoryofnepal_hotels", 200),
        ("google_maps", 100),
    ],
    "restaurants": [
        ("directoryofnepal_restaurants", 200),
        ("google_maps", 100),
    ],
    "pharmacies": [
        ("directoryofnepal_pharmacies", 100),
        ("google_maps", 100),
    ],
    "hospitals": [
        ("google_maps", 100),
    ],
    "clinics": [
        ("nepalyp_clinics", 100),
        ("google_maps", 100),
    ],
    "banks": [
        ("nepalyp_banks", 100),
        ("google_maps", 50),
    ],
    "schools": [
        ("nepalyp_schools", 100),
    ],
    "colleges": [
        ("nepalyp_colleges", 100),
    ],
    "bakeries": [
        ("nepalyp_bakers", 100),
        ("google_maps", 50),
    ],
    "travel_agencies": [
        ("nepalyp_travel_agents", 100),
        ("nepalyp_tour_operators", 100),
    ],
    "car_rentals": [
        ("nepalyp_car_rental", 100),
    ],
    "petrol_stations": [
        ("nepalyp_petrol_stations", 100),
    ],
    "supermarkets": [
        ("nepalyp_shopping_centres", 100),
    ],
    "resorts": [
        ("nepalyp_resorts", 100),
    ],
    "hostels": [
        ("nepalyp_homestays", 100),
    ],
}

# Reduce limits for smaller cities
CITY_MULTIPLIERS = {
    "Kathmandu": 1.0,
    "Pokhara": 0.7,
    "Biratnagar": 0.5,
    "Birgunj": 0.5,
    "Butwal": 0.5,
    "Dharan": 0.5,
    "Lalitpur": 0.7,
    "Bhaktapur": 0.7,
}


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


def main():
    """Main execution function."""
    print("=" * 80)
    print("🚀 BULK DATA COLLECTION SCRIPT (SIMPLE)")
    print("=" * 80)
    print()
    
    # Login
    print("🔐 Logging in...")
    session = requests.Session()
    response = session.post(
        f"{BASE_URL}/auth/login",
        json={"email": "admin@example.com", "password": "admin123"}
    )
    
    if response.status_code != 200:
        print(f"❌ Login failed: {response.status_code}")
        sys.exit(1)
    
    print("✅ Login successful")
    print()
    
    # Create jobs
    created = 0
    skipped = 0
    failed = 0
    
    for city in CITIES:
        multiplier = CITY_MULTIPLIERS.get(city, 0.5)
        print(f"\n📍 {city} (multiplier: {multiplier})")
        print("-" * 80)
        
        for category_name, sources in CATEGORY_SOURCE_MAP.items():
            category_id = get_category_id(category_name)
            
            if not category_id:
                continue
            
            for source_name, base_limit in sources:
                source_id = get_source_id(source_name)
                
                if not source_id:
                    continue
                
                # Adjust limit based on city
                max_results = int(base_limit * multiplier)
                
                # Create job
                try:
                    response = session.post(
                        f"{BASE_URL}/jobs/",
                        json={
                            "category_id": category_id,
                            "location": city,
                            "source_ids": [source_id],
                            "max_results": max_results
                        }
                    )
                    
                    if response.status_code in [200, 201]:
                        print(f"  ✅ {category_name:20s} / {source_name:30s} / limit={max_results}")
                        created += 1
                    else:
                        # Check if it's a duplicate
                        if "already exists" in response.text.lower() or "duplicate" in response.text.lower():
                            print(f"  ⚠️  {category_name:20s} / {source_name:30s} (already exists)")
                            skipped += 1
                        else:
                            print(f"  ❌ {category_name:20s} / {source_name:30s} ({response.status_code})")
                            failed += 1
                    
                    time.sleep(0.3)  # Small delay
                    
                except Exception as e:
                    print(f"  ❌ {category_name:20s} / {source_name:30s} (error: {str(e)[:50]})")
                    failed += 1
    
    # Summary
    print()
    print("=" * 80)
    print("📊 SUMMARY")
    print("=" * 80)
    print(f"✅ Created: {created} jobs")
    print(f"⚠️  Skipped: {skipped} jobs (duplicates)")
    print(f"❌ Failed:  {failed} jobs")
    print()
    
    if created > 0:
        print("🎉 Jobs are queued — Celery worker is processing them!")
        print()
        print("📈 Monitor progress:")
        print()
        print("  docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c \\")
        print("    \"SELECT status, COUNT(*) FROM scrape_jobs GROUP BY status;\"")
        print()
        print("  docker logs gen_scraper-worker-1 --tail 50 -f")
        print()
    
    print("=" * 80)


if __name__ == "__main__":
    main()
