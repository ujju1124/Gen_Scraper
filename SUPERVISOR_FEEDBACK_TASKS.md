# 🔧 Supervisor Feedback - Critical Tasks

**Date**: May 6, 2026  
**Status**: ⚠️ **CRITICAL BUG IDENTIFIED**

---

## 🚨 Critical Issue: Merge Rate Bug

### Problem:
- **Current Merge Rate**: 0.25% (12 merged records out of 4,790)
- **Expected Merge Rate**: 15-20% (720-960 merged records)
- **Impact**: Same hotels appearing as separate records from different sources

### Root Cause (Suspected):
1. Merging only runs within single jobs (not across jobs from different sources)
2. `dedup_key` mismatch between sources (different name normalization)
3. `MergingPipeline` not being called at all for some jobs

---

## 📋 Task List (In Order)

### ✅ Task 0: Start Docker Desktop
**Status**: ⏳ **WAITING**

**Action Required**:
1. Start Docker Desktop
2. Wait for green indicator
3. Run: `docker-compose up -d`

---

### 🔍 Task 1: Diagnose Merge Rate Bug (DO FIRST)

**Status**: ⏳ **READY TO RUN**

**Script Created**: `diagnose-merge-bug.ps1`

**Steps**:
1. Start Docker Desktop
2. Run: `.\diagnose-merge-bug.ps1`
3. Save all 4 outputs
4. Analyze results

**What We're Checking**:
- **Step 1**: Duplicate hotel names in DB
- **Step 2**: `dedup_key` consistency across sources
- **Step 3**: Merger run history by job
- **Step 4**: Worker logs for merging activity

**Expected Findings**:
- Hotels like "Hotel Barahi", "Hotel Himalaya", "Hotel Everest" appearing multiple times
- Different `dedup_key` values for same business from different sources
- Merging only happening within single jobs, not across jobs
- `MergingPipeline` not being called or failing silently

**DO NOT PROCEED** to Task 2 until root cause is identified.

---

### ✅ Task 2: Fix the Merge Bug

**Status**: ✅ **COMPLETE** (verified and working)

**Fix Implemented**: ✅
- Created `backend/tasks/merge_task.py` with `CrossJobMergingPipeline` class
- Created `merge_all_sources()` Celery task
- Added API endpoints: `POST /api/v1/admin/merge-all-sources`, `GET /api/v1/admin/merge-status`
- Created `run-merge-fix.ps1` automated script

**Results**: ✅
- **Merge rate**: 53.62% (859 merged / 1,602 processed)
- **Cross-source merges**: 134 records from multiple sources
- **Exact matching**: 226 records (113 groups)
- **Fuzzy matching**: 633 records (9 groups)

**Verification**: ✅
- Cross-source merging working correctly
- Fuzzy matching NOT creating false positives
- All large merge groups verified as legitimate
- High merge rate explained by scraper over-collection (separate issue)

**Files Created**:
- `backend/tasks/merge_task.py`
- `backend/routers/admin.py` (updated)
- `run-merge-fix.ps1`
- `MERGE_BUG_DIAGNOSIS_RESULTS.md`
- `MERGE_FIX_COMPLETE.md`
- `MERGE_FIX_VERIFIED.md`

**See**: `MERGE_FIX_VERIFIED.md` for complete verification report

---

### 🧪 Task 3: Test Selector Healing System

**Status**: ⏸️ **BLOCKED** (waiting for Task 2 completion)

**Purpose**: Test the healing system with a real broken selector

**Steps**:
1. Find current Booking.com selectors
2. Break one selector intentionally
3. Run a Booking.com job via frontend
4. Check heal log
5. Check worker logs for healing activity
6. Restore correct selector if healing didn't auto-fix

**Expected Behavior**:
- Job runs but returns 0 or partial results
- Heal log shows PENDING entry for `hotel_name` selector
- If AUTO confidence ≥ 0.7 → selector auto-healed
- If AUTO confidence < 0.7 → MANUAL fallback, shows in admin panel

---

### 🌍 Task 4: Expand to More Cities

**Status**: ⏸️ **BLOCKED** (waiting for Task 2 completion)

**Purpose**: Add data for underrepresented cities

**Target Cities**:
- Biratnagar, Birgunj, Butwal, Hetauda, Dharan

**Categories**:
- Hotels, Restaurants, Hospitals, Pharmacies, Banks

**Source**: NepalYP (reliable, not blocked)

**Goal**: 8,000+ total records after this batch

**Critical Rule**: Do NOT collect more data until merge is working correctly!

---

### 🚀 Task 5: Railway Deployment

**Status**: ⏸️ **BLOCKED** (waiting for all fixes)

**Purpose**: Deploy to Railway so product has a real URL

**Platform**: Railway Hobby tier ($5/month)

**Steps**:
1. Create Railway account at railway.app
2. Create new project → Deploy from GitHub repo
3. Add PostgreSQL plugin
4. Add Redis plugin
5. Set all environment variables from `.env`
6. Handle Camoufox `shm_size` workaround for Railway
7. Verify all services healthy at Railway URL

**Documentation**: `docs/railway_deployment.md` (already exists)

---

## 🎯 Critical Rules

1. ✅ **Fix Tasks 1 and 2 (merge bug) before doing anything else**
2. ✅ **Run full test suite after each task**
3. ✅ **Do not add new features until merge bug is fixed**
4. ✅ **Do not collect more data until merge is working correctly**

---

## 📊 Current Status

### What's Working:
- ✅ 4,790 records collected
- ✅ All features implemented
- ✅ All tests passing
- ✅ System stable

### What's Broken:
- ❌ **Merge rate: 0.25% (should be 15-20%)**
- ❌ Duplicate businesses not being merged
- ❌ Same hotel appearing 2-3 times from different sources

### Impact:
- Data quality issue
- Inflated record count
- Poor user experience (duplicates in search results)
- Needs immediate fix before demo/deployment

---

## 🚀 Next Steps

### Immediate (Right Now):
1. **Start Docker Desktop**
2. **Run**: `.\diagnose-merge-bug.ps1`
3. **Save all outputs**
4. **Analyze results**
5. **Identify root cause**

### After Diagnosis:
1. Implement fix in `backend/tasks/merge_task.py`
2. Create `CrossJobMergingPipeline` class
3. Add API endpoint to trigger manual merge
4. Add button in admin panel
5. Run merge on existing 4,790 records
6. Verify 200-500+ records merged
7. Write tests
8. Run full test suite

### After Fix Verified:
1. Test selector healing system (Task 3)
2. Expand to more cities (Task 4)
3. Deploy to Railway (Task 5)

---

## 📞 Quick Commands

### Start System:
```powershell
docker-compose up -d
```

### Run Diagnosis:
```powershell
.\diagnose-merge-bug.ps1
```

### Check Merge Rate:
```powershell
docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c "SELECT COUNT(*) as total, COUNT(CASE WHEN merged_from_sources IS NOT NULL THEN 1 END) as merged, ROUND(100.0 * COUNT(CASE WHEN merged_from_sources IS NOT NULL THEN 1 END) / COUNT(*), 2) as merge_rate_percent FROM cleaned_results;"
```

### View Duplicates:
```powershell
docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -c "SELECT name, city, COUNT(*) FROM cleaned_results GROUP BY name, city HAVING COUNT(*) > 1 ORDER BY COUNT(*) DESC LIMIT 20;"
```

---

## 📝 Files Created

1. **diagnose-merge-bug.ps1** - Automated diagnostic script
2. **SUPERVISOR_FEEDBACK_TASKS.md** - This file (task breakdown)

---

## ⏱️ Estimated Timeline

- **Task 1 (Diagnosis)**: 10 minutes
- **Task 2 (Fix)**: 2-3 hours
- **Task 3 (Healing Test)**: 30 minutes
- **Task 4 (More Cities)**: 1-2 hours
- **Task 5 (Deployment)**: 1 hour

**Total**: 5-7 hours

---

## 🎯 Success Criteria

### Task 1:
- ✅ All 4 diagnostic queries run successfully
- ✅ Root cause identified
- ✅ Clear understanding of why merge rate is low

### Task 2:
- ✅ Merge rate increases to 15-20% (200-500+ merged records)
- ✅ Same hotels from different sources properly merged
- ✅ All tests passing
- ✅ Manual merge trigger working in admin panel

### Task 3:
- ✅ Broken selector detected
- ✅ Healing system activates
- ✅ Selector auto-healed or flagged for manual review
- ✅ Heal log shows correct entries

### Task 4:
- ✅ 8,000+ total records
- ✅ Better city distribution
- ✅ More balanced data

### Task 5:
- ✅ Live Railway URL
- ✅ All services healthy
- ✅ Database migrated
- ✅ Public demo accessible

---

**START WITH TASK 1 RIGHT NOW** ⚡

Once Docker is running, execute:
```powershell
.\diagnose-merge-bug.ps1
```

Then paste all 4 outputs for analysis.

---

**Last Updated**: May 6, 2026  
**Priority**: 🔴 **CRITICAL**  
**Status**: ⏳ **Waiting for Docker to start**
