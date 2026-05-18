#!/usr/bin/env python3
"""Trigger NepalYP clinics test job for Phase 7."""

from tasks.scrape_task import scrape_task

job_id = "013dd502-374f-4c11-ad44-66bfdeb746ab"
print(f"Triggering NepalYP clinics test job: {job_id}")
result = scrape_task.delay(job_id)
print(f"✅ Task sent to Celery: {result.id}")
print("Check worker logs for progress")
