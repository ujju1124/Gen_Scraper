"""
Monitor Progress for Priority 6 - Multi-City Data Collection

Shows current statistics and progress toward 50,000 record goal.

Usage:
    python monitor_progress.py
"""
import subprocess
import sys


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


def main():
    print("\n" + "="*70)
    print("PRIORITY 6 - MULTI-CITY DATA COLLECTION PROGRESS")
    print("="*70 + "\n")
    
    # Total records
    print("📊 TOTAL RECORDS:")
    total_output = run_query("SELECT COUNT(*) as total_records FROM cleaned_results;")
    print(total_output)
    
    # Extract total number
    try:
        lines = total_output.strip().split('\n')
        for line in lines:
            if line.strip().isdigit():
                total = int(line.strip())
                progress = (total / 50000) * 100
                print(f"Progress: {total:,} / 50,000 ({progress:.1f}%)")
                print(f"Remaining: {50000 - total:,} records\n")
                break
    except:
        pass
    
    # Records by city
    print("📍 RECORDS BY CITY:")
    city_output = run_query(
        "SELECT city, COUNT(*) as records FROM cleaned_results "
        "GROUP BY city ORDER BY COUNT(*) DESC;"
    )
    print(city_output)
    
    # Records by category
    print("\n📂 RECORDS BY CATEGORY:")
    category_output = run_query(
        "SELECT c.name as category, COUNT(*) as records "
        "FROM cleaned_results cr "
        "JOIN categories c ON cr.category_id = c.id "
        "GROUP BY c.name ORDER BY COUNT(*) DESC LIMIT 10;"
    )
    print(category_output)
    
    # Records by source
    print("\n🔗 RECORDS BY SOURCE:")
    source_output = run_query(
        "SELECT s.display_name as source, COUNT(*) as records "
        "FROM cleaned_results cr "
        "JOIN sources s ON cr.source_id = s.id "
        "GROUP BY s.display_name ORDER BY COUNT(*) DESC LIMIT 10;"
    )
    print(source_output)
    
    # Recent jobs
    print("\n⏱️  RECENT JOBS (Last 10):")
    jobs_output = run_query(
        "SELECT id, status, location, "
        "(SELECT COUNT(*) FROM cleaned_results WHERE job_id = scrape_jobs.id) as results, "
        "created_at "
        "FROM scrape_jobs "
        "ORDER BY created_at DESC LIMIT 10;"
    )
    print(jobs_output)
    
    # Running jobs
    print("\n🔄 CURRENTLY RUNNING JOBS:")
    running_output = run_query(
        "SELECT id, location, status, created_at "
        "FROM scrape_jobs "
        "WHERE status = 'RUNNING' "
        "ORDER BY created_at DESC;"
    )
    print(running_output)
    
    print("="*70 + "\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user\n")
        sys.exit(0)
    except Exception as e:
        print(f"\nError: {e}\n")
        sys.exit(1)
