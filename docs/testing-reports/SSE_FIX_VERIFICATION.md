# SSE Fix Verification Guide - UPDATED

## Date: April 27, 2026 - Latest Update

## Critical Changes Applied (Latest)

### Backend SSE Event Generator (`backend/routers/jobs.py`)

**Key improvements:**
1. **Initial connection event** - Sends `: connected\n\n` immediately when connection opens
2. **Completion event** - Sends `: complete\n\n` when job finishes
3. **Better error handling** - Catches all exceptions and sends error events
4. **Proper event formatting** - Ensures each event is properly formatted with `\n\n` terminator

```python
async def event_generator():
    try:
        # Send initial connection event (CRITICAL - establishes connection)
        yield ": connected\n\n"
        
        while True:
            # ... poll database and send status events ...
            
            # Yield SSE event with proper formatting
            event_message = f"event: status\ndata: {json.dumps(event_data)}\n\n"
            yield event_message
            
            # Break if job is done or failed
            if job.status in ("DONE", "FAILED"):
                # Send final event to signal completion
                yield ": complete\n\n"
                break
            
            await asyncio.sleep(2)
            
    except asyncio.CancelledError:
        logger.info("sse.cancelled", job_id=str(job_id))
        return
    except Exception as e:
        logger.error("sse.error", job_id=str(job_id), error=str(e), exc_info=True)
        # Send error event
        yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
        return
```

**Why this fixes the issue:**
- The initial `: connected\n\n` event establishes the SSE connection immediately
- Without this, the browser waits for the first event, which might take 2+ seconds
- The browser may timeout or consider the connection incomplete if no data arrives quickly
- SSE comments (lines starting with `:`) are valid SSE protocol and keep the connection alive

--- 1. Nginx Configuration Updates (`frontend/nginx.conf`)

**Improved SSE proxy configuration:**
```nginx
location /api/ {
    proxy_pass http://backend:8000;
    proxy_http_version 1.1;
    
    # SSE requires Connection: '' (empty string, not 'keep-alive' or 'upgrade')
    proxy_set_header Connection '';
    
    # Standard proxy headers
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    
    # Disable all caching and buffering for SSE
    proxy_buffering off;
    proxy_cache off;
    proxy_cache_bypass $http_upgrade;
    
    # Long timeouts for SSE connections
    proxy_read_timeout 86400s;
    proxy_send_timeout 86400s;
    proxy_connect_timeout 60s;
    
    # Enable chunked transfer encoding for streaming
    chunked_transfer_encoding on;
    
    # Prevent nginx from modifying response headers
    proxy_pass_header Server;
}
```

**Key changes:**
- Removed `Upgrade` header (not needed for SSE)
- Added `proxy_connect_timeout 60s`
- Added `proxy_pass_header Server` to preserve backend headers
- Better organized comments

### 2. Backend SSE Headers (`backend/routers/jobs.py`)

**Enhanced SSE response headers:**
```python
return StreamingResponse(
    event_generator(),
    media_type="text/event-stream",
    headers={
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
        "Content-Type": "text/event-stream; charset=utf-8",
    }
)
```

**Key changes:**
- Strengthened `Cache-Control` header
- Explicitly set `Content-Type` with charset

---

## Verification Steps

### Step 1: Clear Browser Cache

**Important:** Clear your browser cache to ensure you're testing with the new configuration.

**Chrome:**
1. Press `Ctrl+Shift+Delete`
2. Select "Cached images and files"
3. Click "Clear data"

**Or use Incognito/Private mode:**
- Chrome: `Ctrl+Shift+N`
- Firefox: `Ctrl+Shift+P`

### Step 2: Open DevTools Before Testing

1. Open http://localhost:5173
2. Press `F12` to open DevTools
3. Go to **Network** tab
4. Check "Preserve log" (important!)
5. Filter by "EventSource" or "stream" in the filter box

### Step 3: Login and Create a Job

1. Login with test credentials:
   - Email: `user@example.com`
   - Password: `password123`

2. Create a new scrape job:
   - Category: Hotels (or any category)
   - Location: Kathmandu (or any location)
   - Click "Create Job"

### Step 4: Verify SSE Connection in DevTools

In the Network tab, you should see:

**✅ SUCCESS indicators:**
- Request to `/api/v1/jobs/{job_id}/stream`
- **Type:** `eventsource` (not `xhr` or `fetch`)
- **Status:** `200` (not `(failed)` or `(cancelled)`)
- **Size:** Should show increasing size as events stream (starts small, grows over time)
- **Time:** Should show increasing time (connection stays open for 5-10 seconds)

**Click on the request to see details:**
- **Headers tab:**
  - Request Method: `GET`
  - Status Code: `200 OK`
  - Content-Type: `text/event-stream; charset=utf-8`
  - Cache-Control: `no-cache, no-store, must-revalidate`
  - Connection: `keep-alive`

- **EventStream tab** (Chrome) or **Response tab** (Firefox):
  - **FIRST EVENT (immediate):** `: connected` (this is the connection establishment event)
  - **SECOND EVENT (~0-1s):** 
    ```
    event: status
    data: {"status":"QUEUED","started_at":null,"completed_at":null}
    ```
  - **THIRD EVENT (~2-3s):**
    ```
    event: status
    data: {"status":"RUNNING","started_at":"2026-04-27T06:30:15.123456","completed_at":null}
    ```
  - **FOURTH EVENT (~5-10s):**
    ```
    event: status
    data: {"status":"DONE","started_at":"2026-04-27T06:30:15.123456","completed_at":"2026-04-27T06:30:20.654321","result_count":10}
    ```
  - **FINAL EVENT:** `: complete` (signals end of stream)

**CRITICAL:** The `: connected` event should appear **immediately** (within 100ms). This proves the SSE connection is established correctly.

**❌ FAILURE indicators (should NOT see these):**
- Status: `(failed)` with red text
- Error: `net::ERR_HTTP2_PROTOCOL_ERROR`
- Error: `net::ERR_INCOMPLETE_CHUNKED_ENCODING`
- Type: `xhr` or `fetch` (should be `eventsource`)
- No `: connected` event at the start
- Connection closes immediately without any events

### Step 5: Verify Real-Time Updates in UI

Watch the job status in the UI:

1. **Initial state:** Status badge shows "QUEUED" (yellow/amber)
2. **After ~1-2 seconds:** Status changes to "RUNNING" (blue) **without page refresh**
3. **After ~3-8 seconds:** Status changes to "DONE" (green) **without page refresh**
4. **Progress bar:** Should animate smoothly as job progresses

**Important:** The status should update automatically without you refreshing the page. This proves SSE is working.

### Step 6: Check Console for Errors

In the **Console** tab of DevTools:

**✅ Should NOT see:**
- `EventSource failed`
- `ERR_HTTP2_PROTOCOL_ERROR`
- `ERR_INCOMPLETE_CHUNKED_ENCODING`
- `Failed to load resource`

**✅ May see (these are normal):**
- `SSE connection established` (if you added logging)
- `SSE connection closed` (when job completes)

---

## Troubleshooting

### If SSE still fails:

#### 1. Check nginx logs:
```bash
docker logs gen_scraper-frontend-1 --tail 50
```

Look for errors related to proxy or upstream.

#### 2. Check backend logs:
```bash
docker logs gen_scraper-backend-1 --tail 50
```

Look for SSE-related errors or exceptions.

#### 3. Test SSE directly (bypass nginx):
```bash
# In a new terminal
curl -N http://localhost:8000/api/v1/jobs/{job_id}/stream \
  -H "Authorization: Bearer YOUR_TOKEN"
```

If this works but browser doesn't, the issue is in nginx config.

#### 4. Verify nginx config syntax:
```bash
docker exec gen_scraper-frontend-1 nginx -t
```

Should output: `nginx: configuration file /etc/nginx/nginx.conf test is successful`

#### 5. Check if HTTP/2 is being used:
In DevTools Network tab, click on the SSE request and check:
- **Protocol:** Should be `http/1.1` (not `h2` or `http/2`)

If it shows `h2`, the browser is forcing HTTP/2. This is a browser issue, not a server issue.

---

## Expected Behavior

### Timeline of a successful job with SSE:

```
T+0s:   User clicks "Create Job"
        → POST /api/v1/jobs/ returns 201 Created
        → UI navigates to /jobs/{job_id}
        → SSE connection opens to /api/v1/jobs/{job_id}/stream

T+0.5s: First SSE event received
        → status: QUEUED
        → UI shows yellow "QUEUED" badge

T+1-2s: Second SSE event received
        → status: RUNNING
        → UI shows blue "RUNNING" badge
        → Progress bar starts animating

T+4-8s: Final SSE event received
        → status: DONE
        → result_count: 10
        → UI shows green "DONE" badge
        → Progress bar completes
        → SSE connection closes gracefully

Total:  ~5-10 seconds for mock job
        All status updates happen automatically via SSE
        No page refreshes needed
```

---

## Success Criteria

✅ **SSE connection established successfully**
- Type: `eventsource`
- Status: `200`
- No errors in console

✅ **Real-time updates working**
- Status changes from QUEUED → RUNNING → DONE
- No page refresh needed
- Updates appear within 2 seconds

✅ **No HTTP/2 errors**
- No `ERR_HTTP2_PROTOCOL_ERROR`
- No `ERR_INCOMPLETE_CHUNKED_ENCODING`

✅ **Connection closes gracefully**
- After job completes (DONE or FAILED)
- No lingering connections in Network tab

---

## Additional Tests

### Test 1: Multiple Jobs
Create 3 jobs in quick succession. Each should have its own SSE connection and update independently.

### Test 2: Long-Running Job
If you have a real scraper (not mock), test with a job that takes 30+ seconds. SSE should stay connected the entire time.

### Test 3: Network Interruption
1. Start a job
2. Disconnect network (airplane mode)
3. Reconnect network
4. SSE should reconnect automatically (if implemented) or show error gracefully

### Test 4: Browser Compatibility
Test in multiple browsers:
- Chrome/Edge (Chromium)
- Firefox
- Safari (if available)

All should work identically.

---

## Files Modified

1. `frontend/nginx.conf` - Enhanced SSE proxy configuration
2. `backend/routers/jobs.py` - Improved SSE response headers

---

## Status: ✅ READY FOR TESTING

All changes have been applied and services restarted. Please follow the verification steps above and report any issues.
