-- Verification script for self-healing fixes

-- Check 1: Verify field_hints are updated
SELECT 'CHECK 1: Field Hints Updated' as check_name;
SELECT name, 
       field_hints->'review_count' as review_count_hint,
       field_hints->'name' as name_hint
FROM sources 
WHERE name = 'google_maps';

-- Check 2: Monitor new healing attempts (will show after next scrape)
SELECT 'CHECK 2: Recent Healing Attempts' as check_name;
SELECT field_name, 
       confidence, 
       status, 
       healed_at,
       CASE 
         WHEN confidence >= 0.70 THEN 'SHOULD HEAL'
         ELSE 'TOO LOW'
       END as expected_outcome
FROM selector_heal_log 
WHERE healed_at > NOW() - INTERVAL '10 minutes'
ORDER BY healed_at DESC 
LIMIT 10;

-- Check 3: Verify html_snapshot_hash will be saved (check after next successful scrape)
SELECT 'CHECK 3: HTML Snapshot Hash Status' as check_name;
SELECT field_name,
       CASE 
         WHEN html_snapshot_hash IS NULL THEN 'NOT SAVED YET'
         ELSE 'SAVED'
       END as hash_status,
       LEFT(html_snapshot_hash, 8) as hash_preview
FROM scraper_selectors 
WHERE source_id = (SELECT id FROM sources WHERE name = 'google_maps')
ORDER BY field_name;

-- Check 4: Current job progress
SELECT 'CHECK 4: Job Progress' as check_name;
SELECT status, COUNT(*) as count
FROM scrape_jobs 
WHERE status != 'CANCELLED'
GROUP BY status
ORDER BY status;

-- Check 5: Total results
SELECT 'CHECK 5: Total Results' as check_name;
SELECT COUNT(*) as total_results FROM cleaned_results;
