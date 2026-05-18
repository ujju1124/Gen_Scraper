"""
Direct merge execution script - runs cross-job merge synchronously.
"""
import sys
from database import SessionLocal
from scrapers.merger import MergingPipeline

def main():
    db = SessionLocal()
    try:
        print("Starting cross-job merge...")
        merger = MergingPipeline(db)
        
        # Run cross-job merge
        result = merger.run_cross_job()
        
        print(f"\n✅ Merge completed!")
        print(f"Total merged: {result['total_merged']}")
        print(f"New merges: {result['new_merges']}")
        print(f"Updated merges: {result['updated_merges']}")
        
    except Exception as e:
        print(f"\n❌ Merge failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    main()
