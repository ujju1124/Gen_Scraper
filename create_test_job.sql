-- Create a test job for Booking.com with 3 results
INSERT INTO scrape_jobs (user_id, category_id, location, source_ids, max_results, status)
VALUES (1, 1, 'Kathmandu', ARRAY[1], 3, 'QUEUED')
RETURNING id, location, source_ids, max_results, status;
