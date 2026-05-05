"""
Real-time monitoring for Batch 1 jobs
Checks status every 30 seconds until all jobs complete
"""
import subprocess
import time
import sys
from datetime import datetime

# Batch 1 job IDs
BATCH1_JOBS = [
    '86f69afb-481c-403b-8091-f9e80857610e',  # Hotels
    'c103449d-b0a2-4f88-8b7e-864dedcf43bc',  # Restaurants
    '73a78966-95a6-41cb-a1c7-abe09592c0ed',  # Hospitals
    'bf3b7e5d-ec70-498d-ae21-2a2b220ec527',  # Banks
    '27ead6d0-ba7a-406a-a798-077580f49b58',  # Schools
]

def run_query(query: str) -> str:
    """Run a PostgreSQL query and return output."""
    result = subprocess.run(
        [
            "docker", "exec", "gen_scraper-postgres-1",
            "psql", "-U", "scraper", "-d", "scraper_db",
            "-c", query
        ],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        return result.stdout
    else:
        return f"Error: {result.stderr}"


def check_jobs():
    """Check status of all Batch 1 jobs."""
    job_ids_str = "', '".join(BATCH1_JOBS)
    query = f"""
    SELECT 
        substring(id::text, 1, 8) as job_id,
        status,
        (SELECT name FROM categories WHERE id = category_id) as category,
        (SELECT COUNT(*) FROM cleaned_results WHERE job_id = scrape_jobs.id) as results
    FROM scrape_jobs 
    WHERE id IN ('{job_ids_str}')
    ORDER BY created_at;
    """
    
    return run_query(query)


def get_total_records():
    """Get total record count."""
    result = run_query("SELECT COUNT(*) as total FROM cleaned_results;")
    try:
        lines = result.strip().split('\n')
        for line in lines:
            if line.strip().isdigit():
                return int(line.strip())
    except:
        pass
    return 0


def all_jobs_complete(status_output: str) -> bool:
    """Check if all jobs are DONE or FAILED."""
    return 'RUNNING' not in status_output and 'QUEUED' not in status_output and 'PENDING' not in status_output


def main():
    print("\n" + "="*70)
    print("BATCH 1 MONITORING - Real-time Job Tracker")
    print("="*70)
    print("\nMonitoring 5 Kathmandu jobs:")
    print("  1. Hotels (200 limit)")
    print("  2. Restaurants (200 limit)")
    print("  3. Hospitals (200 limit)")
    print("  4. Banks (100 limit)")
    print("  5. Schools (100 limit)")
    print("\nPress Ctrl+C to stop monitoring\n")
    print("="*70 + "\n")
    
    iteration = 0
    
    try:
        while True:
            iteration += 1
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            print(f"\n[{timestamp}] Check #{iteration}")
            print("-" * 70)
            
            # Check job status
            status = check_jobs()
            print(status)
            
            # Check if all complete
            if all_jobs_complete(status):
                print("\n" + "="*70)
                print("✓ ALL BATCH 1 JOBS COMPLETE!")
                print("="*70)
                
                # Final statistics
                total = get_total_records()
                print(f"\n📊 Total records in database: {total:,}")
                
                print("\n📊 Records by city:")
                city_stats = run_query(
                    "SELECT city, COUNT(*) as records FROM cleaned_results "
                    "GROUP BY city ORDER BY COUNT(*) DESC LIMIT 10;"
                )
                print(city_stats)
                
                print("\n" + "="*70)
                print("Ready for Batch 2!")
                print("Run: python bulk_job_creator.py --batch 2")
                print("="*70 + "\n")
                break
            
            # Show total progress
            total = get_total_records()
            progress = (total / 50000) * 100
            print(f"\n📊 Total Progress: {total:,} / 50,000 ({progress:.1f}%)")
            
            print(f"\nNext check in 30 seconds... (Ctrl+C to stop)")
            print("-" * 70)
            
            time.sleep(30)
            
    except KeyboardInterrupt:
        print("\n\n⚠ Monitoring stopped by user")
        print("Jobs are still running in the background")
        print("Run this script again to resume monitoring\n")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
