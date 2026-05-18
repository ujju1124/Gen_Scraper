#!/usr/bin/env python3
"""
Quick script to create a test job for verifying the Celery solo pool fix.
"""
import requests
import sys

# API configuration
API_URL = "http://localhost:8000"
LOGIN_ENDPOINT = f"{API_URL}/api/v1/auth/login"
JOBS_ENDPOINT = f"{API_URL}/api/v1/jobs"

# Admin credentials (from seed.py)
ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "admin123"

def main():
    print("🔐 Logging in as admin...")
    
    # Create a session to handle cookies
    session = requests.Session()
    
    # Login to get access token (stored in cookie)
    login_response = session.post(
        LOGIN_ENDPOINT,
        json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        }
    )
    
    if login_response.status_code != 200:
        print(f"❌ Login failed: {login_response.status_code}")
        print(login_response.text)
        sys.exit(1)
    
    print(f"✅ Logged in successfully")
    
    # Create test job (session automatically sends cookies)
    print("\n📝 Creating test job...")
    print("   Location: Kathmandu")
    print("   Category: Hotels (ID=1)")
    print("   Max Results: 5")
    print("   Sources: Booking.com (auto-selected)")
    
    job_response = session.post(
        JOBS_ENDPOINT,
        json={
            "location": "Kathmandu",
            "category_id": 1,
            "max_results": 5
        }
    )
    
    if job_response.status_code != 201:
        print(f"❌ Job creation failed: {job_response.status_code}")
        print(job_response.text)
        sys.exit(1)
    
    job_data = job_response.json()
    job_id = job_data["id"]
    
    print(f"\n✅ Test job created successfully!")
    print(f"   Job ID: {job_id}")
    print(f"   Status: {job_data['status']}")
    
    print("\n📊 Monitor progress:")
    print(f"   docker logs gen_scraper-worker-1 -f")
    print("\n🔍 Check results:")
    print(f"   docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c \"SELECT COUNT(*) FROM cleaned_results WHERE job_id = '{job_id}';\"")
    print("\n🌐 View in admin panel:")
    print(f"   http://localhost:5173/admin/jobs/{job_id}")

if __name__ == "__main__":
    main()
