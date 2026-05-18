#!/usr/bin/env python3
"""Trigger NepalYP detail extraction test job"""
import sys
sys.path.insert(0, '/app')

from tasks.scrape_task import scrape_task

job_id = "e3ca8f48-865c-44d6-a436-3ab34340b400"
print(f"Triggering NepalYP detail extraction test job: {job_id}")
result = scrape_task.delay(job_id)

print(f"✅ Task sent to Celery: {result.id}")
print("Check worker logs for progress")
