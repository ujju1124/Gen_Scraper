"""Run cross-job merge on all existing records."""
import sys
sys.path.insert(0, '/app')

from tasks.merge_task import run_merge_sync

print("Starting cross-job merge on all existing records...")
print("This may take a few minutes...")

stats = run_merge_sync()

print("\n=== MERGE COMPLETE ===")
print(f"Total records processed: {stats['total_records_processed']}")
print(f"Exact merged groups:     {stats['exact_merged_groups']}")
print(f"Fuzzy merged groups:     {stats['fuzzy_merged_groups']}")
print(f"Total merged groups:     {stats['merged_groups']}")
print("=====================")
