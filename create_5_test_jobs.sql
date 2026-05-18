-- Create 5 test jobs for scale testing
-- Each job will trigger healing for the broken selectors

-- ============================================================
-- JOB #1: Booking.com (Test name selector healing)
-- ============================================================
INSERT INTO scrape_jobs (
    user_id,
    category_id,
    source_ids, 
    location, 
    status, 
    max_results,
    created_at
) VALUES (
    1,  -- admin user
    1,  -- hotels
    ARRAY[1],  -- booking_com
    'Paris',
    'QUEUED',
    5,  -- Small job for quick testing
    NOW()
) RETURNING id, source_ids, location, status;

-- ============================================================
-- JOB #2: NepalYP Banks (Test name selector healing)
-- ============================================================
INSERT INTO scrape_jobs (
    user_id,
    category_id,
    source_ids, 
    location, 
    status, 
    max_results,
    created_at
) VALUES (
    1,  -- admin user
    13,  -- banks
    ARRAY[15],  -- nepalyp_banks
    'Kathmandu',
    'QUEUED',
    5,
    NOW()
) RETURNING id, source_ids, location, status;

-- ============================================================
-- JOB #3: Google Maps (Test rating selector healing)
-- ============================================================
INSERT INTO scrape_jobs (
    user_id,
    category_id,
    source_ids, 
    location, 
    status, 
    max_results,
    created_at
) VALUES (
    1,  -- admin user
    6,  -- restaurants
    ARRAY[32],  -- google_maps
    'New York',
    'QUEUED',
    5,
    NOW()
) RETURNING id, source_ids, location, status;

-- ============================================================
-- JOB #4: Booking.com (Test address selector healing)
-- ============================================================
INSERT INTO scrape_jobs (
    user_id,
    category_id,
    source_ids, 
    location, 
    status, 
    max_results,
    created_at
) VALUES (
    1,  -- admin user
    1,  -- hotels
    ARRAY[1],  -- booking_com
    'London',
    'QUEUED',
    5,
    NOW()
) RETURNING id, source_ids, location, status;

-- ============================================================
-- JOB #5: NepalYP Banks (Test phone selector healing)
-- ============================================================
INSERT INTO scrape_jobs (
    user_id,
    category_id,
    source_ids, 
    location, 
    status, 
    max_results,
    created_at
) VALUES (
    1,  -- admin user
    13,  -- banks
    ARRAY[15],  -- nepalyp_banks
    'Pokhara',
    'QUEUED',
    5,
    NOW()
) RETURNING id, source_ids, location, status;

-- ============================================================
-- VERIFICATION: Show all queued jobs
-- ============================================================
SELECT 
    j.id,
    j.source_ids,
    j.location,
    j.status,
    j.max_results
FROM scrape_jobs j
WHERE j.status = 'QUEUED'
ORDER BY j.created_at DESC
LIMIT 10;

SELECT '✅ All 5 test jobs created and queued' AS final_status;
