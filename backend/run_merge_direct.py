"""
Direct merge execution script.
Runs cross-job merge synchronously without needing API authentication.
"""
import sys
sys.path.insert(0, '/app')

from tasks.merge_task import run_merge_sync

if __name__ == "__main__":
    print("Starting cross-job merge...")
    stats = run_merge_sync()
    print("\n✅ Merge complete!")
    print(f"Statistics: {stats}")
