"""Trigger Google Maps rating test job"""
import sys
sys.path.insert(0, '/app')

from tasks.scrape_task import scrape_task

job_id = "808c1e42-0cf3-4fe9-9000-84e1b4f62416"
print(f"Triggering Google Maps rating test job: {job_id}")
result = scrape_task.delay(job_id)
print(f"✅ Task sent to Celery: {result.id}")
