"""Trigger NepalYP phone test job"""
import sys
sys.path.insert(0, '/app')

from tasks.scrape_task import scrape_task

job_id = "3592a2de-bab8-43ad-a3f1-801b90a06c37"
print(f"Triggering NepalYP phone test job: {job_id}")
result = scrape_task.delay(job_id)
print(f"✅ Task sent to Celery: {result.id}")
