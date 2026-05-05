# Task 12: Celery Integration with Orchestrator - Implementation Summary

## Overview
Successfully integrated the Phase 2 ScraperOrchestrator and CleaningPipeline with the Celery task system, while preserving the Phase 1 mock task as a fallback controlled by the `MOCK_MODE` environment variable.

---

## Changes Made

### 1. Updated `backend/tasks/scrape_task.py`

**Main Entry Point:**
- Created new `scrape_task()` function registered as `tasks.scrape_task`
- Routes to either mock or real implementation based on `settings.MOCK_MODE`
- Logs routing decision with structured logging

**Mock Implementation (Phase 1 Preserved):**
- Renamed `mock_scrape_task()` to `mock_scrape_task_impl()`
- Preserved all original Phase 1 functionality:
  - Sleeps random 3-8 seconds
  - Generates exactly 10 synthetic hotel records
  - Inserts into both `raw_results` and `cleaned_results`
  - Updates job status: QUEUED → RUNNING → DONE/FAILED

**Real Implementation (Phase 2 New):**
- Created `real_scrape_task_impl()` function
- Integrates ScraperOrchestrator for multi-source scraping:
  - Loads job from database
  - Sets status to RUNNING
  - Calls `orchestrator.run_async()` with `asyncio.run()` wrapper
  - Receives raw results and failed source IDs
- Integrates CleaningPipeline for data processing:
  - Groups results by source_id
  - Runs 7-step cleaning pipeline for each source
  - Saves to `raw_results` and `cleaned_results` tables
- Updates job with completion status:
  - Sets status to DONE
  - Saves `failed_source_ids` array for retry logic
  - Logs total cleaned results and failures
- Exception handling:
  - Sets status to FAILED on error
  - Saves error message to database
  - Logs with structured logging
  - Always closes database session in finally block

### 2. Updated `backend/routers/jobs.py`

**Import Changes:**
- Changed from `from tasks.scrape_task import mock_scrape_task`
- To `from tasks.scrape_task import scrape_task`

**Task Dispatch:**
- Changed from `task = mock_scrape_task.delay(job_id)`
- To `task = scrape_task.delay(job_id)`

**Documentation:**
- Updated docstring to reflect routing behavior based on MOCK_MODE

### 3. Configuration (Already Complete from Previous Fixes)

**`backend/config.py`:**
- `MOCK_MODE: bool = False` already added to Settings model

**`.env` and `.env.example`:**
- `MOCK_MODE=false` already added

---

## Architecture

### Task Routing Flow

```
POST /api/v1/jobs
    ↓
scrape_task.delay(job_id)
    ↓
scrape_task() [Celery task]
    ↓
    ├─ if MOCK_MODE=true → mock_scrape_task_impl()
    │                       └─ Phase 1 synthetic data
    │
    └─ if MOCK_MODE=false → real_scrape_task_impl()
                            ├─ ScraperOrchestrator.run_async()
                            │  ├─ Load sources
                            │  ├─ Group by domain
                            │  ├─ Run scrapers (parallel/sequential)
                            │  └─ Return (raw_results, failed_source_ids)
                            │
                            └─ CleaningPipeline.process()
                               ├─ Save raw results
                               ├─ Normalize data
                               ├─ Dedup within job
                               ├─ Dedup cross job
                               ├─ Validate fields
                               ├─ Compute completeness
                               └─ Save cleaned results
```

### Async Bridge

The orchestrator is async but Celery tasks are sync. We bridge them with:

```python
raw_results, failed_source_ids = asyncio.run(
    orchestrator.run_async(db, str(job_uuid))
)
```

This creates a new event loop, runs the async orchestrator, and returns results synchronously.

---

## Key Features

### 1. Backward Compatibility
- Phase 1 mock task fully preserved
- Can switch between mock and real with environment variable
- No breaking changes to API or database schema

### 2. Failure Tracking
- Orchestrator returns `failed_source_ids` list
- Saved to `scrape_jobs.failed_source_ids` column
- Enables retry logic in future phases

### 3. Structured Logging
- All routing decisions logged
- Orchestrator completion logged with counts
- Cleaning pipeline completion logged
- Job completion logged with results and failures

### 4. Error Handling
- Try/except/finally pattern ensures database cleanup
- Job status set to FAILED on exception
- Error message saved to database
- Structured logging with exc_info=True for stack traces

### 5. Database Session Management
- Single session created at start
- Passed to orchestrator and cleaning pipeline
- Always closed in finally block
- Prevents connection leaks

---

## Testing Strategy

### Phase 1 Mock Mode (MOCK_MODE=true)
1. Set `MOCK_MODE=true` in `.env`
2. Restart worker: `docker-compose restart worker`
3. Create job via `POST /api/v1/jobs`
4. Verify:
   - Job status: QUEUED → RUNNING → DONE
   - 10 synthetic results in `cleaned_results`
   - Task completes in 3-8 seconds
   - Logs show "task.routing_to_mock"

### Phase 2 Real Mode (MOCK_MODE=false)
1. Set `MOCK_MODE=false` in `.env`
2. Restart worker: `docker-compose restart worker`
3. Create job via `POST /api/v1/jobs` with Booking.com source
4. Verify:
   - Job status: QUEUED → RUNNING → DONE
   - Results in both `raw_results` and `cleaned_results`
   - `failed_source_ids` is empty or contains failed sources
   - Logs show "task.routing_to_real"
   - Orchestrator and cleaning pipeline logs present

---

## Completion Checklist

- [x] 12.1 MOCK_MODE config added (already done in previous fixes)
- [x] 12.2 Renamed `mock_scrape_task` to `mock_scrape_task_impl`
- [x] 12.3 Implemented `real_scrape_task_impl()` with orchestrator and cleaner
- [x] 12.4 Created main `scrape_task()` router function
- [x] 12.5 Added `asyncio.run()` wrapper for async orchestrator
- [x] 12.6 Database session management in try/finally block
- [x] Updated `backend/routers/jobs.py` to use new task name
- [x] Updated docstrings and comments

---

## Next Steps

**Task 13: Structured Logging**
- Verify all structured log events are emitted
- Check Sentry tags on exceptions
- Confirm JSON formatting

**Task 14: End-to-End Pipeline Test**
- Test with MOCK_MODE=false
- Verify Booking.com scraper runs (returns empty list until selectors work)
- Verify cleaning pipeline processes results
- Verify failed_source_ids tracking
- Test fallback with MOCK_MODE=true

**Task 15: Documentation and Cleanup**
- Add docstrings to all classes and methods
- Add type hints to all function signatures
- Update README with Phase 2 architecture
- Document HUMAN CHECKPOINT process

---

## Files Modified

1. `backend/tasks/scrape_task.py` - Complete rewrite with routing logic
2. `backend/routers/jobs.py` - Updated import and task dispatch

## Files Referenced (No Changes)

1. `backend/config.py` - MOCK_MODE already configured
2. `.env` - MOCK_MODE already set
3. `.env.example` - MOCK_MODE already documented
4. `backend/scrapers/orchestrator.py` - Used by real implementation
5. `backend/scrapers/cleaner.py` - Used by real implementation

---

**Task 12 Status: ✅ COMPLETE**

All subtasks completed successfully. The Celery integration now supports both Phase 1 mock mode and Phase 2 real scraping with orchestrator and cleaning pipeline.
