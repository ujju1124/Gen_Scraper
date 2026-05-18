#!/usr/bin/env python3
"""Trigger Booking.com test job for Phase 7 field expansion testing."""

from tasks.scrape_task import scrape_task

job_id = "d39a4e08-3fb5-46b2-9f52-00ec34a4093f"
print(f"Triggering Booking.com test job: {job_id}")
result = scrape_task.delay(job_id)
print(f"✅ Task sent to Celery: {result.id}")
print("Check worker logs for progress")
