#!/usr/bin/env python3
"""
Quick test script to verify NepalYP category scrapers work.
Run this from the project root directory.
"""
import requests
import time
import sys

# Configuration
BASE_URL = "http://localhost:8000"
ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "admin123"

def login():
    """Login and get access token"""
    print("🔐 Logging in...")
    response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    
    if response.status_code != 200:
        print(f"❌ Login failed: {response.text}")
        sys.exit(1)
    
    token = response.json()["access_token"]
    print("✅ Login successful")
    return token

def get_sources(token):
    """Get all sources"""
    print("\n📋 Fetching sources...")
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/api/v1/sources", headers=headers)
    
    if response.status_code != 200:
        print(f"❌ Failed to fetch sources: {response.text}")
        sys.exit(1)
    
    sources = response.json()
    
    # Find NepalYP category sources
    nepalyp_sources = {}
    for source in sources:
        if source["name"].startswith("nepalyp_"):
            nepalyp_sources[source["name"]] = source
            print(f"  ✓ Found: {source['display_name']} (ID: {source['id']}, Active: {source['is_active']})")
    
    return nepalyp_sources

def create_job(token, category_id, source_id, location="Kathmandu", max_results=25):
    """Create a scrape job"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.post(f"{BASE_URL}/api/v1/jobs", headers=headers, json={
        "category_id": category_id,
        "location": location,
        "source_ids": [source_id],
        "max_results": max_results
    })
    
    if response.status_code != 201:
        print(f"❌ Failed to create job: {response.text}")
        return None
    
    return response.json()

def monitor_job(token, job_id, job_name):
    """Monitor job until completion"""
    headers = {"Authorization": f"Bearer {token}"}
    print(f"\n⏳ Monitoring {job_name} job (ID: {job_id})...")
    
    while True:
        response = requests.get(f"{BASE_URL}/api/v1/jobs/{job_id}", headers=headers)
        
        if response.status_code != 200:
            print(f"❌ Failed to fetch job status: {response.text}")
            return None
        
        job = response.json()
        status = job["status"]
        
        print(f"  Status: {status}", end="\r")
        
        if status == "DONE":
            print(f"\n✅ {job_name} job completed!")
            return job
        elif status == "FAILED":
            print(f"\n❌ {job_name} job failed!")
            print(f"  Error: {job.get('error_message', 'Unknown error')}")
            return job
        
        time.sleep(3)

def get_results(token, job_id):
    """Get job results"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/api/v1/jobs/{job_id}/results", headers=headers)
    
    if response.status_code != 200:
        print(f"❌ Failed to fetch results: {response.text}")
        return []
    
    data = response.json()
    return data.get("results", [])

def main():
    print("=" * 60)
    print("NepalYP Category Scrapers Verification Test")
    print("=" * 60)
    
    # Login
    token = login()
    
    # Get sources
    sources = get_sources(token)
    
    if not sources:
        print("\n❌ No NepalYP category sources found!")
        print("   Make sure you've run the source creation script.")
        sys.exit(1)
    
    # Define test cases
    test_cases = [
        {
            "name": "Restaurants",
            "source_name": "nepalyp_restaurants",
            "category_id": 6,
        },
        {
            "name": "Pharmacies",
            "source_name": "nepalyp_pharmacies",
            "category_id": 9,
        },
        {
            "name": "Hospitals",
            "source_name": "nepalyp_hospitals",
            "category_id": 10,
        },
    ]
    
    # Run tests
    results_summary = []
    
    for test in test_cases:
        print(f"\n{'=' * 60}")
        print(f"TEST: {test['name']}")
        print(f"{'=' * 60}")
        
        source = sources.get(test["source_name"])
        
        if not source:
            print(f"❌ Source '{test['source_name']}' not found!")
            results_summary.append({
                "name": test["name"],
                "status": "SKIPPED",
                "reason": "Source not found"
            })
            continue
        
        if not source["is_active"]:
            print(f"⚠️  Source '{test['source_name']}' is not active!")
            results_summary.append({
                "name": test["name"],
                "status": "SKIPPED",
                "reason": "Source not active"
            })
            continue
        
        # Create job
        print(f"\n🚀 Creating {test['name']} scrape job...")
        job = create_job(token, test["category_id"], source["id"])
        
        if not job:
            results_summary.append({
                "name": test["name"],
                "status": "FAILED",
                "reason": "Failed to create job"
            })
            continue
        
        # Monitor job
        completed_job = monitor_job(token, job["id"], test["name"])
        
        if not completed_job:
            results_summary.append({
                "name": test["name"],
                "status": "FAILED",
                "reason": "Failed to monitor job"
            })
            continue
        
        # Get results
        if completed_job["status"] == "DONE":
            print(f"\n📊 Fetching results...")
            results = get_results(token, job["id"])
            
            print(f"\n✅ Results: {len(results)} items")
            
            if results:
                print(f"\n📝 Sample results (first 3):")
                for i, result in enumerate(results[:3], 1):
                    print(f"  {i}. {result.get('name', 'N/A')}")
                    print(f"     Address: {result.get('address', 'N/A')}")
                    print(f"     City: {result.get('city', 'N/A')}")
                    print()
            
            results_summary.append({
                "name": test["name"],
                "status": "SUCCESS",
                "job_id": job["id"],
                "count": len(results),
                "samples": [r.get("name", "N/A") for r in results[:3]]
            })
        else:
            results_summary.append({
                "name": test["name"],
                "status": "FAILED",
                "job_id": job["id"],
                "error": completed_job.get("error_message", "Unknown error")
            })
    
    # Print summary
    print(f"\n{'=' * 60}")
    print("SUMMARY")
    print(f"{'=' * 60}")
    
    for result in results_summary:
        print(f"\n{result['name']}:")
        print(f"  Status: {result['status']}")
        
        if result["status"] == "SUCCESS":
            print(f"  Job ID: {result['job_id']}")
            print(f"  Results: {result['count']}")
            print(f"  Samples:")
            for i, name in enumerate(result["samples"], 1):
                print(f"    {i}. {name}")
        elif result["status"] == "FAILED":
            print(f"  Job ID: {result.get('job_id', 'N/A')}")
            print(f"  Error: {result.get('error', result.get('reason', 'Unknown'))}")
        else:
            print(f"  Reason: {result.get('reason', 'Unknown')}")
    
    # Check if all passed
    all_passed = all(r["status"] == "SUCCESS" for r in results_summary)
    
    print(f"\n{'=' * 60}")
    if all_passed:
        print("✅ ALL TESTS PASSED!")
        print("NepalYP category scrapers are working correctly.")
    else:
        print("❌ SOME TESTS FAILED")
        print("Check the logs above for details.")
        print("\nTo view worker logs:")
        print("  docker logs gen_scraper-worker-1 --tail=50")
    print(f"{'=' * 60}\n")
    
    sys.exit(0 if all_passed else 1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
