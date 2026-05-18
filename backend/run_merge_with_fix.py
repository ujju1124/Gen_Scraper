#!/usr/bin/env python3
"""
Run cross-job merge pipeline with placeholder coordinate fix.
This script tests the fix for the critical fuzzy matching bug.
"""
from database import SessionLocal
from tasks.merge_task import CrossJobMergingPipeline

def main():
    db = SessionLocal()
    
    try:
        print("Starting cross-job merge pipeline with placeholder coordinate fix...")
        print()
        
        pipeline = CrossJobMergingPipeline(db)
        stats = pipeline.run()
        
        print()
        print("=" * 60)
        print("MERGE STATISTICS")
        print("=" * 60)
        print(f"Total records processed: {stats['total_records_processed']}")
        print(f"Exact merged groups: {stats['exact_merged_groups']}")
        print(f"Exact merged records: {stats['exact_merged_records']}")
        print(f"Fuzzy merged groups: {stats['fuzzy_merged_groups']}")
        print(f"Fuzzy merged records: {stats['fuzzy_merged_records']}")
        print(f"Total merged groups: {stats['total_merged_groups']}")
        print(f"Total merged records: {stats['total_merged_records']}")
        print(f"Merge rate: {stats['merge_rate_percent']}%")
        print("=" * 60)
        
    finally:
        db.close()

if __name__ == "__main__":
    main()
