# Email Notification Event Loop Verification

**Purpose**: Verify that Task 20 email notification implementation doesn't cause asyncio event loop errors in the Celery worker.

---

## Background

The email notification feature uses `asyncio.run()` inside a synchronous Celery task. This can potentially cause issues if:
1. An event loop is already running
2. The event loop isn't properly closed
3. There are nested asyncio.run() calls

We need to verify the implementation works correctly in production.

---

## Test Procedure

### Step 1: Start Services
```bash
# Make sure all services are running
docker-compose up -d

# Verify services are healthy
docker-compose ps
```

Expected output:
```
gen_scraper-backend-1    running
gen_scraper-worker-1     running
gen_scraper-postgres-1   running
gen_scraper-redis-1      running
gen_scraper-frontend-1   running
```

### Step 2: Open Playwright Browser (Manual Testing)

**Option A: Using Playwright Codegen (Recommended)**
```bash
cd frontend
npx playwright codegen http://localhost:5173
```

This will open a browser with recording tools. Follow these steps:
1. Navigate to http://localhost:5173/login
2. Login with:
   - Email: `admin@example.com`
   - Password: `admin123`
3. Click "Create Job" or navigate to job creation page
4. Fill in the form:
   - **Category**: Hotels
   - **Location**: Kathmandu
   - **Sources**: Check "NepalYP" (or any active source)
   - **Max Results**: 25
5. Click "Start Scraping" or "Submit"
6. Wait for job to appear in the list
7. Note the Job ID from the URL or job list

**Option B: Manual Browser Testing**
1. Open http://localhost:5173 in your browser
2. Login as admin
3. Create a job with the settings above
4. Note the Job ID

### Step 3: Monitor Job Completion

Wait for the job to complete (should take 3-8 seconds for mock mode, or 30-60 seconds for real scraping).

You can monitor via:
- Frontend: Watch the job status change from QUEUED → RUNNING → DONE/FAILED
- API: `curl http://localhost:8000/api/v1/jobs/{job_id}`

### Step 4: Check Worker Logs

Once the job completes, immediately check the worker logs:

```bash
docker logs gen_scraper-worker-1 --tail=100
```

### Step 5: Search for Specific Patterns

Look for email-related logs and errors:

```bash
# Check for email notification logs
docker logs gen_scraper-worker-1 --tail=100 | grep -i "email"

# Check for asyncio/event loop errors
docker logs gen_scraper-worker-1 --tail=100 | grep -i "error\|loop\|runtime"

# Check for SMTP-related logs
docker logs gen_scraper-worker-1 --tail=100 | grep -i "smtp"
```

---

## What to Look For

### ✅ Success Indicators

**If SMTP is NOT configured** (default):
```
email_notification_skipped reason=smtp_not_configured job_id=...
```

**If SMTP IS configured**:
```
email_notification_sent job_id=... recipient=... status=DONE
```

**Job completion logs**:
```
job.done job_id=... result_count=10 duration_seconds=...
```

### ❌ Error Indicators

**Event loop errors** (BAD):
```
RuntimeError: asyncio.run() cannot be called from a running event loop
RuntimeError: Event loop is closed
RuntimeError: This event loop is already running
```

**Email errors that crash the job** (BAD):
```
job.failed job_id=... error=... (with email-related error)
```

**Uncaught exceptions** (BAD):
```
Traceback (most recent call last):
  ...
  email_service.py
  ...
```

### ⚠️ Expected Warnings (OK)

**Email skipped** (OK - SMTP not configured):
```
email_notification_skipped reason=smtp_not_configured
```

**Email failed but job succeeded** (OK - fail-safe working):
```
email_notification_failed job_id=... error=...
job.done job_id=... result_count=10
```

---

## Expected Behavior

### Scenario 1: SMTP Not Configured (Default)
1. Job completes successfully (DONE)
2. Worker logs show: `email_notification_skipped reason=smtp_not_configured`
3. No errors or exceptions
4. Job results are saved correctly

### Scenario 2: SMTP Configured but Connection Fails
1. Job completes successfully (DONE)
2. Worker logs show: `email_notification_failed job_id=... error=...`
3. No RuntimeError or event loop errors
4. Job results are saved correctly

### Scenario 3: SMTP Configured and Working
1. Job completes successfully (DONE)
2. Worker logs show: `email_notification_sent job_id=... recipient=...`
3. Email is sent to user
4. No errors or exceptions

---

## Test Report Template

Please fill this out after running the test:

### Test Execution

**Date/Time**: _____________  
**Job ID**: _____________  
**Job Status**: DONE / FAILED  
**Duration**: _____ seconds  

### Worker Logs Analysis

**Email notification log found?**: YES / NO  
**Log message**: 
```
[Paste the email-related log line here]
```

**Any errors found?**: YES / NO  
**Error details** (if any):
```
[Paste error logs here]
```

**Event loop errors?**: YES / NO  
**RuntimeError found?**: YES / NO  

### Full Worker Logs (Last 100 Lines)
```bash
docker logs gen_scraper-worker-1 --tail=100
```

Output:
```
[Paste full output here]
```

### Grep Results

**Email logs**:
```bash
docker logs gen_scraper-worker-1 --tail=100 | grep -i "email"
```
Output:
```
[Paste output here]
```

**Error logs**:
```bash
docker logs gen_scraper-worker-1 --tail=100 | grep -i "error\|loop\|runtime"
```
Output:
```
[Paste output here]
```

---

## Troubleshooting

### If You See Event Loop Errors

The issue is in `backend/tasks/scrape_task.py`. The current implementation:
```python
try:
    asyncio.run(send_job_completion_email(job, db))
except Exception as e:
    logger.error("email_notification_failed", job_id=job_id, error=str(e))
```

**Potential fixes**:

1. **Check if loop is running first**:
```python
try:
    loop = asyncio.get_event_loop()
    if loop.is_running():
        # Create a new loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    asyncio.run(send_job_completion_email(job, db))
except Exception as e:
    logger.error("email_notification_failed", job_id=job_id, error=str(e))
```

2. **Use loop.run_until_complete() instead**:
```python
try:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(send_job_completion_email(job, db))
    loop.close()
except Exception as e:
    logger.error("email_notification_failed", job_id=job_id, error=str(e))
```

### If Email Crashes the Job

This means the try/except isn't catching the error. Check:
1. Is the try/except in the right place?
2. Is the exception being raised before the try block?
3. Are there multiple email calls?

---

## Quick Test Commands

```bash
# 1. Check if services are running
docker-compose ps

# 2. Create a test job (via frontend or API)
# [Use Playwright browser as described above]

# 3. Wait for job to complete
sleep 10

# 4. Check worker logs
docker logs gen_scraper-worker-1 --tail=100

# 5. Search for email logs
docker logs gen_scraper-worker-1 --tail=100 | grep -i "email"

# 6. Search for errors
docker logs gen_scraper-worker-1 --tail=100 | grep -i "error\|loop\|runtime"

# 7. Check job status via API
curl http://localhost:8000/api/v1/jobs/{JOB_ID}
```

---

## Next Steps

### If Test Passes ✅
- Email notification is working correctly
- No event loop issues
- Can proceed to NepalYP category verification

### If Test Fails ❌
- Fix the event loop issue in `scrape_task.py`
- Re-run the test
- Do NOT proceed until this is fixed

---

**Status**: ⏳ **AWAITING TEST EXECUTION**

Please run the test using Playwright browser and report back with the logs!
