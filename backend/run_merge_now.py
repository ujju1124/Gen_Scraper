"""
Run cross-job merge directly without Celery.
"""
import sys
sys.path.insert(0, '/app')

from database import SessionLocal
from scrapers.merger import MergingPipeline

def main():
    db = SessionLocal()
    try:
        print("Starting cross-job merge...")
        merger = MergingPipeline(db)
        stats = merger.run_cross_job()
        
        print("\n=== MERGE COMPLETE ===")
        print(f"Total records processed: {stats['total_records_processed']}")
        print(f"Exact merged groups: {stats['exact_merged_groups']}")
        print(f"Exact merged records: {stats['exact_merged_records']}")
        print(f"Fuzzy merged groups: {stats['fuzzy_merged_groups']}")
        print(f"Fuzzy merged records: {stats['fuzzy_merged_records']}")
        print(f"Total merged groups: {stats['total_merged_groups']}")
        print(f"Total merged records: {stats['total_merged_records']}")
        print(f"Merge rate: {stats['merge_rate_percent']:.2f}%")
        
    finally:
        db.close()

if __name__ == "__main__":
    main()
