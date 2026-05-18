"""
Trigger a Celery task for an existing job.
"""
import sys

job_id = "8c2ff158-f954-4a35-a49e-21f1f3b7ed8a"

# Import Celery app
import os
os.chdir('backend')
sys.path.insert(0, os.getcwd())

from celery import Celery

# Create Celery app
app = Celery('scraper')
app.config_from_object('celeryconfig')

# Send task
result = app.send_task('tasks.scrape_task', args=[job_id])

print(f"✅ Dispatched task: {result.id}")
print(f"📊 Job ID: {job_id}")
print(f"\n📊 Monitor logs with: docker-compose logs -f worker")
