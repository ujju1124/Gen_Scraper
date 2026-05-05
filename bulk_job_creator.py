"""
Bulk Job Creator for Priority 6 - Multi-City Data Collection

Creates scraping jobs in batches across 8 cities and 6 high-value categories.
Goal: 50,000+ total records before product demo.

Usage:
    python bulk_job_creator.py --batch 1
    python bulk_job_creator.py --batch 2
    ... up to batch 10
"""
import httpx
import time
import argparse
import sys
from typing import List, Dict

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

# API Configuration
API_BASE_URL = "http://localhost:8000/api/v1"
LOGIN_EMAIL = "admin@example.com"
LOGIN_PASSWORD = "admin123"

# Job Configuration
CITIES = ["Kathmandu", "Pokhara", "Biratnagar", "Birgunj", "Butwal", "Dharan", "Lalitpur", "Bhaktapur"]

# Category configurations: (category_slug, source_names, max_results)
CATEGORIES = [
    ("hotels", ["booking_com", "nepalyp", "directoryofnepal_hotels"], 200),
    ("restaurants", ["nepalyp_restaurants", "directoryofnepal_restaurants"], 200),
    ("hospitals", ["nepalyp_hospitals"], 200),
    ("banks", ["nepalyp_banks"], 100),
    ("schools", ["nepalyp_schools"], 100),
    ("pharmacies", ["nepalyp_pharmacies", "directoryofnepal_pharmacies"], 100),
]

# Batch definitions (5 jobs per batch)
BATCHES = [
    # Batch 1: Kathmandu (5 jobs)
    [
        ("Kathmandu", "hotels", 200),
        ("Kathmandu", "restaurants", 200),
        ("Kathmandu", "hospitals", 200),
        ("Kathmandu", "banks", 100),
        ("Kathmandu", "schools", 100),
    ],
    # Batch 2: Kathmandu + Pokhara (5 jobs)
    [
        ("Kathmandu", "pharmacies", 100),
        ("Pokhara", "hotels", 200),
        ("Pokhara", "restaurants", 200),
        ("Pokhara", "hospitals", 200),
        ("Pokhara", "banks", 100),
    ],
    # Batch 3: Pokhara + Biratnagar (5 jobs)
    [
        ("Pokhara", "schools", 100),
        ("Pokhara", "pharmacies", 100),
        ("Biratnagar", "hotels", 200),
        ("Biratnagar", "restaurants", 200),
        ("Biratnagar", "hospitals", 200),
    ],
    # Batch 4: Biratnagar + Birgunj (5 jobs)
    [
        ("Biratnagar", "banks", 100),
        ("Biratnagar", "schools", 100),
        ("Biratnagar", "pharmacies", 100),
        ("Birgunj", "hotels", 200),
        ("Birgunj", "restaurants", 200),
    ],
    # Batch 5: Birgunj + Butwal (5 jobs)
    [
        ("Birgunj", "hospitals", 200),
        ("Birgunj", "banks", 100),
        ("Birgunj", "schools", 100),
        ("Birgunj", "pharmacies", 100),
        ("Butwal", "hotels", 200),
    ],
    # Batch 6: Butwal + Dharan (5 jobs)
    [
        ("Butwal", "restaurants", 200),
        ("Butwal", "hospitals", 200),
        ("Butwal", "banks", 100),
        ("Butwal", "schools", 100),
        ("Butwal", "pharmacies", 100),
    ],
    # Batch 7: Dharan (5 jobs)
    [
        ("Dharan", "hotels", 200),
        ("Dharan", "restaurants", 200),
        ("Dharan", "hospitals", 200),
        ("Dharan", "banks", 100),
        ("Dharan", "schools", 100),
    ],
    # Batch 8: Dharan + Lalitpur (5 jobs)
    [
        ("Dharan", "pharmacies", 100),
        ("Lalitpur", "hotels", 200),
        ("Lalitpur", "restaurants", 200),
        ("Lalitpur", "hospitals", 200),
        ("Lalitpur", "banks", 100),
    ],
    # Batch 9: Lalitpur + Bhaktapur (5 jobs)
    [
        ("Lalitpur", "schools", 100),
        ("Lalitpur", "pharmacies", 100),
        ("Bhaktapur", "hotels", 200),
        ("Bhaktapur", "restaurants", 200),
        ("Bhaktapur", "hospitals", 200),
    ],
    # Batch 10: Bhaktapur (3 jobs)
    [
        ("Bhaktapur", "banks", 100),
        ("Bhaktapur", "schools", 100),
        ("Bhaktapur", "pharmacies", 100),
    ],
]


def login() -> httpx.Client:
    """Login and return authenticated client with cookies."""
    print(f"Logging in as {LOGIN_EMAIL}...")
    
    # Create a client that persists cookies and follows redirects
    client = httpx.Client(timeout=30.0, follow_redirects=True)
    
    response = client.post(
        f"{API_BASE_URL}/auth/login",
        json={"email": LOGIN_EMAIL, "password": LOGIN_PASSWORD}
    )
    
    if response.status_code != 200:
        raise Exception(f"Login failed: {response.status_code} - {response.text}")
    
    # Cookies are automatically stored in the client
    print("✓ Login successful")
    return client


def get_category_id(client: httpx.Client, category_slug: str) -> int:
    """Get category ID by slug."""
    response = client.get(f"{API_BASE_URL}/categories")
    
    if response.status_code != 200:
        raise Exception(f"Failed to fetch categories: {response.status_code} - {response.text}")
    
    try:
        data = response.json()
        # API returns {"items": [...]} structure
        categories = data.get("items", data) if isinstance(data, dict) else data
    except Exception as e:
        raise Exception(f"Failed to parse categories response: {e}. Response: {response.text[:200]}")
    
    for cat in categories:
        if cat.get("name") == category_slug or cat.get("slug") == category_slug:
            return cat["id"]
    
    raise Exception(f"Category not found: {category_slug}. Available: {[c.get('name') or c.get('slug') for c in categories[:5]]}")


def get_source_ids(client: httpx.Client, source_names: List[str]) -> List[int]:
    """Get source IDs by names."""
    response = client.get(f"{API_BASE_URL}/admin/sources")
    
    if response.status_code != 200:
        raise Exception(f"Failed to fetch sources: {response.status_code}")
    
    data = response.json()
    # API returns {"items": [...]} structure
    sources = data.get("items", data) if isinstance(data, dict) else data
    source_ids = []
    
    for source_name in source_names:
        for source in sources:
            if source["name"] == source_name and source["is_active"]:
                source_ids.append(source["id"])
                break
    
    return source_ids


def create_job(client: httpx.Client, city: str, category_slug: str, max_results: int) -> Dict:
    """Create a single scraping job."""
    # Get category ID
    category_id = get_category_id(client, category_slug)
    
    # Get source IDs for this category
    category_config = next((c for c in CATEGORIES if c[0] == category_slug), None)
    if not category_config:
        raise Exception(f"Category config not found: {category_slug}")
    
    source_names = category_config[1]
    source_ids = get_source_ids(client, source_names)
    
    if not source_ids:
        print(f"  ⚠ No active sources found for {category_slug}, skipping...")
        return None
    
    # Create job
    job_data = {
        "location": city,
        "category_id": category_id,
        "source_ids": source_ids,
        "max_results": max_results
    }
    
    print(f"  Creating: {city} - {category_slug} (limit={max_results}, sources={len(source_ids)})")
    
    response = client.post(f"{API_BASE_URL}/jobs", json=job_data)
    
    if response.status_code != 201:
        print(f"  ✗ Failed: {response.status_code} - {response.text}")
        return None
    
    job = response.json()
    print(f"  ✓ Created: Job ID {job['id']}")
    return job


def wait_for_jobs_completion(client: httpx.Client, job_ids: List[str], check_interval: int = 30):
    """Wait for all jobs to complete."""
    print(f"\nWaiting for {len(job_ids)} jobs to complete...")
    print("Checking every 30 seconds...")
    
    completed = set()
    
    while len(completed) < len(job_ids):
        time.sleep(check_interval)
        
        for job_id in job_ids:
            if job_id in completed:
                continue
            
            response = client.get(f"{API_BASE_URL}/jobs/{job_id}")
            
            if response.status_code == 200:
                job = response.json()
                status = job.get("status")
                
                if status in ["DONE", "FAILED"]:
                    completed.add(job_id)
                    result_count = job.get("result_count", 0)
                    print(f"  ✓ Job {job_id[:8]}... {status} ({result_count} results)")
        
        if len(completed) < len(job_ids):
            remaining = len(job_ids) - len(completed)
            print(f"  ... {remaining} jobs still running")
    
    print(f"\n✓ All {len(job_ids)} jobs completed!")


def get_total_records() -> int:
    """Get total record count from database."""
    import subprocess
    result = subprocess.run(
        [
            "docker", "exec", "gen_scraper-postgres-1",
            "psql", "-U", "scraper", "-d", "scraper_db",
            "-t", "-c", "SELECT COUNT(*) FROM cleaned_results;"
        ],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        return int(result.stdout.strip())
    return 0


def get_records_by_city():
    """Get record count by city."""
    import subprocess
    result = subprocess.run(
        [
            "docker", "exec", "gen_scraper-postgres-1",
            "psql", "-U", "scraper", "-d", "scraper_db",
            "-c", "SELECT city, COUNT(*) as records FROM cleaned_results GROUP BY city ORDER BY COUNT(*) DESC;"
        ],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        print("\n" + result.stdout)


def run_batch(batch_number: int):
    """Run a specific batch of jobs."""
    if batch_number < 1 or batch_number > len(BATCHES):
        print(f"Error: Batch number must be between 1 and {len(BATCHES)}")
        return
    
    batch_index = batch_number - 1
    batch_jobs = BATCHES[batch_index]
    
    print(f"\n{'='*60}")
    print(f"BATCH {batch_number}/{len(BATCHES)} - {len(batch_jobs)} jobs")
    print(f"{'='*60}\n")
    
    # Login
    client = login()
    
    # Create jobs
    print(f"\nCreating {len(batch_jobs)} jobs...")
    job_ids = []
    
    for city, category_slug, max_results in batch_jobs:
        try:
            job = create_job(client, city, category_slug, max_results)
            if job:
                job_ids.append(job["id"])
            time.sleep(1)  # Small delay between job creations
        except Exception as e:
            print(f"  ✗ Error creating job: {e}")
            import traceback
            traceback.print_exc()
    
    if not job_ids:
        print("\n✗ No jobs created successfully")
        client.close()
        return
    
    print(f"\n✓ Created {len(job_ids)} jobs successfully")
    
    # Wait for completion
    wait_for_jobs_completion(client, job_ids)
    
    # Close client
    client.close()
    
    # Show statistics
    print(f"\n{'='*60}")
    print(f"BATCH {batch_number} COMPLETE")
    print(f"{'='*60}")
    
    total = get_total_records()
    print(f"\n📊 Total records in database: {total:,}")
    
    print("\n📊 Records by city:")
    get_records_by_city()
    
    print(f"\n{'='*60}")
    if batch_number < len(BATCHES):
        print(f"Ready for Batch {batch_number + 1}")
        print(f"Run: python bulk_job_creator.py --batch {batch_number + 1}")
    else:
        print("🎉 ALL BATCHES COMPLETE!")
        print(f"Final total: {total:,} records")
    print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(description="Bulk Job Creator for Multi-City Data Collection")
    parser.add_argument("--batch", type=int, required=True, help=f"Batch number (1-{len(BATCHES)})")
    
    args = parser.parse_args()
    
    try:
        run_batch(args.batch)
    except KeyboardInterrupt:
        print("\n\n⚠ Interrupted by user")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
