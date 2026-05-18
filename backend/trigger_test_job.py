#!/usr/bin/env python3
"""Trigger a test job manually"""
import sys
from tasks.scrape_task import scrape_task

if __name__ == "__main__":
    job_id = "5bcc5a12-bd53-48a4-ba29-ee1b7359f9be"
    print(f"Triggering job {job_id}...")
    result = scrape_task.apply_async(args=[job_id])
    print(f"Task ID: {result.id}")
    print(f"Task state: {result.state}")
