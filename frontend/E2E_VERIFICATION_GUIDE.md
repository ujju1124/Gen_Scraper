# End-to-End Verification Guide - Phase 3

**Date**: April 27, 2026  
**Environment**: Docker Production Build (http://localhost:5173)

## Prerequisites

- ✅ Docker containers running: `docker-compose ps`
- ✅ Frontend: http://localhost:5173 (nginx)
- ✅ Backend: http://localhost:8000 (FastAPI)
- ✅ Test users seeded in database

## Task 11.5: Create Job End-to-End ✅

### Test Steps

1. **Login as Regular User**
   - Navigate to: http://localhost:5173/login
   - Credentials: `user@example.com` / `password123`
   - Expected: Redirect to `/dashboard`

2. **Create New Job**
   - On Dashboard, locate "Create New Job" form
   - Select Category: "Hotels"
   - Wait for sources to load
   - Enter Location: "Kathmandu"
   - Select Source: "Booking.com"
   - Click "Create Job"
   - Expected: Redirect to `/jobs/{job_id}`

3. **Verify Job Creation**
   - Check job status page loads
   - Status should be "QUEUED" or "RUNNING"
   - Job details displayed (ID, location, category)
   - Expected: No errors, clean UI

### Verification Checklist

- [ ] Form validation works (required fields)
- [ ] Category dropdown populates from API
- [ ] Sources load when category selected
- [ ] Job creation succeeds
- [ ] Redirect to job status page
- [ ] Job appears in dashboard history table

### API Calls to Monitor

```
POST /api/v1/jobs/
  Request: { category_id, location, source_ids }
  Response: { id, status, created_at, ... }

GET /api/v1/categories/
  Response: { items: [...] }

GET /api/v1/categories/{id}/sources/
  Response: [{ id, name, display_name }]
```

---

## Task 11.6: Admin Panel Filtering ✅

### Test Steps

1. **Login as Admin**
   - Logout if logged in as user
   - Navigate to: http://localhost:5173/login
   - Credentials: `admin@example.com` / `admin123`
   - Expected: Redirect to `/dashboard`

2. **Navigate to Admin Panel**
   - Click "Admin Panel" in navigation
   - URL: http://localhost:5173/admin
   - Expected: Admin results table loads

3. **Test Filters**
   
   **Status Filter:**
   - Select "Approved" from status dropdown
   - Expected: Table updates, only APPROVED results shown
   - Active filter badge appears: "Status: APPROVED"
   
   **Category Filter:**
   - Select "Hotels" from category dropdown
   - Expected: Table updates, only hotel results shown
   - Active filter badge appears: "Category: Hotels"
   
   **City Filter:**
   - Type "Kathmandu" in city input
   - Expected: Table updates, only Kathmandu results shown
   - Active filter badge appears: "City: Kathmandu"
   
   **Multiple Filters:**
   - Apply all three filters simultaneously
   - Expected: Results match all criteria
   - All filter badges displayed
   
   **Clear Filters:**
   - Click "Clear Filters" button
   - Expected: All filters reset, full results shown
   - Filter badges disappear

4. **Test Sorting**
   - Click "Completeness" column header
   - Expected: Results sorted by data_completeness
   - Sort indicator (arrow) appears
   
   - Click "Created At" column header
   - Expected: Results sorted by created_at
   - Sort indicator moves to new column

5. **Test Pagination**
   - If more than 50 results, pagination controls appear
   - Click "Next" button
   - Expected: Page 2 loads, filters preserved
   - Page indicator updates: "Page 2 of X"

### Verification Checklist

- [ ] Admin panel accessible only to admin users
- [ ] TanStack Table v8 renders correctly
- [ ] All filters work independently
- [ ] Multiple filters work together
- [ ] Clear filters button resets all
- [ ] Sorting works on clickable columns
- [ ] Pagination preserves filters
- [ ] Active filters displayed as badges
- [ ] Empty state shown when no results

### API Calls to Monitor

```
GET /api/v1/admin/results/
  Params: { page, page_size, status, category_id, city, sort_by }
  Response: { items: [...], total, pages, page }
```

---

## Task 11.7: SSE Real-Time Updates ✅

### Test Steps

1. **Create a New Job**
   - Login as regular user
   - Create a job (Hotels, Kathmandu, Booking.com)
   - Navigate to job status page: `/jobs/{job_id}`

2. **Monitor Real-Time Updates**
   - Observe the status badge
   - Watch for status changes: QUEUED → RUNNING → DONE
   - Check "Real-time updates active" indicator (green pulsing dot)
   - Result count should update as scraping progresses

3. **Verify SSE Connection**
   - Open Browser DevTools → Network tab
   - Filter by "EventStream" or search for `/stream`
   - Expected: SSE connection to `/api/v1/jobs/{job_id}/stream`
   - Connection status: "pending" (long-lived)
   - Messages received as job progresses

4. **Test SSE Fallback**
   - If SSE fails, should fall back to polling
   - Indicator changes to "Polling for updates..."
   - Status still updates every 5 seconds

5. **Verify Data Preservation**
   - Location field should remain visible during updates
   - All job details preserved (not overwritten by partial updates)
   - SSE updates merge with existing data

### Verification Checklist

- [ ] SSE connection established on job status page
- [ ] Real-time indicator shows "Real-time updates active"
- [ ] Status updates without page refresh
- [ ] Result count updates in real-time
- [ ] Location and other fields preserved
- [ ] Polling fallback works if SSE fails
- [ ] "View Results" button appears when DONE
- [ ] Error message shown when FAILED

### Network Inspection

**SSE Connection:**
```
Request URL: http://localhost:5173/api/v1/jobs/{job_id}/stream
Request Method: GET
Status: 200 OK (pending)
Content-Type: text/event-stream

Event Stream:
event: status
data: {"status":"RUNNING","result_count":5}

event: status
data: {"status":"DONE","result_count":15,"completed_at":"..."}
```

**Nginx Proxy Settings (Critical for SSE):**
```nginx
proxy_buffering off;
proxy_cache off;
proxy_read_timeout 86400s;
```

---

## Task 11.8: Mobile Responsive Design ✅

### Test Steps

1. **Open Chrome DevTools**
   - Press F12 or Ctrl+Shift+I
   - Click "Toggle device toolbar" icon (or Ctrl+Shift+M)
   - Select device: "iPhone 12 Pro" (390x844)

2. **Test Login Page (Mobile)**
   - Navigate to: http://localhost:5173/login
   - Verify:
     - Form is centered and readable
     - Input fields are touch-friendly (min 44px height)
     - Button is full-width or appropriately sized
     - No horizontal scrolling
     - Text is legible (min 16px to prevent zoom)

3. **Test Dashboard (Mobile)**
   - Login and navigate to dashboard
   - Verify:
     - Navigation collapses to hamburger menu
     - Job creation form stacks vertically
     - Job history table is scrollable horizontally
     - Cards stack vertically
     - Buttons are touch-friendly

4. **Test Job Status Page (Mobile)**
   - Navigate to a job status page
   - Verify:
     - Job details grid stacks vertically (1 column)
     - Status badge is visible
     - "View Results" button is accessible
     - Real-time indicator is visible

5. **Test Admin Panel (Mobile)**
   - Login as admin, navigate to admin panel
   - Verify:
     - Filters stack vertically
     - Table scrolls horizontally
     - Pagination controls are accessible
     - Filter badges wrap properly

6. **Test Different Viewports**
   - Mobile: 375px (iPhone SE)
   - Tablet: 768px (iPad)
   - Desktop: 1920px (Full HD)
   - Verify layout adapts at each breakpoint

### Verification Checklist

- [ ] No horizontal scrolling on mobile
- [ ] Touch targets ≥ 44px × 44px
- [ ] Text readable without zooming (≥ 16px)
- [ ] Navigation hamburger menu works
- [ ] Forms stack vertically on mobile
- [ ] Tables scroll horizontally with visible scrollbar
- [ ] Cards and grids adapt to viewport
- [ ] Buttons are full-width or appropriately sized
- [ ] Spacing is consistent across viewports

### Tailwind Breakpoints Used

```css
sm: 640px   /* Small devices */
md: 768px   /* Medium devices (tablets) */
lg: 1024px  /* Large devices (desktops) */
xl: 1280px  /* Extra large devices */
```

---

## Task 11.9: Accessibility Check ✅

### Test Steps

1. **Keyboard Navigation - Login Form**
   - Navigate to: http://localhost:5173/login
   - Press Tab repeatedly
   - Expected tab order:
     1. Email input field
     2. Password input field
     3. Login button
     4. "Don't have an account? Register" link
   - Verify:
     - Focus indicator visible on each element
     - No focus traps
     - Can submit form with Enter key

2. **Keyboard Navigation - Dashboard**
   - Login and navigate to dashboard
   - Press Tab through all interactive elements
   - Verify:
     - Navigation links are accessible
     - Form inputs are accessible
     - Buttons are accessible
     - Table rows are accessible (if clickable)
     - Logout button is accessible

3. **Screen Reader Labels**
   - Check form inputs have labels:
     - `<label for="email">Email</label>`
     - `<input id="email" type="email" />`
   - Check buttons have descriptive text
   - Check images have alt text (if any)

4. **Color Contrast**
   - Text on background meets WCAG AA standards
   - Primary text: slate-900 on white (high contrast)
   - Secondary text: slate-600 on white (sufficient contrast)
   - Button text: white on indigo-600 (high contrast)

5. **Focus Indicators**
   - All interactive elements show focus state
   - Focus ring visible: `focus:ring-2 focus:ring-primary-500`
   - Focus ring not obscured by other elements

6. **ARIA Attributes**
   - Check for proper ARIA labels where needed
   - Progress bars have `role="progressbar"` and `aria-valuenow`
   - Status badges have appropriate roles
   - Loading states have `aria-busy="true"`

### Verification Checklist

- [ ] All interactive elements keyboard accessible
- [ ] Logical tab order (top to bottom, left to right)
- [ ] Focus indicators visible and clear
- [ ] Form inputs have associated labels
- [ ] Buttons have descriptive text
- [ ] Color contrast meets WCAG AA (4.5:1 for text)
- [ ] No keyboard traps
- [ ] Can complete all tasks with keyboard only
- [ ] Screen reader friendly (semantic HTML)

### Accessibility Tools

**Manual Testing:**
- Tab key for keyboard navigation
- Shift+Tab for reverse navigation
- Enter/Space for activation

**Automated Testing (Optional):**
- Chrome DevTools → Lighthouse → Accessibility audit
- axe DevTools browser extension
- WAVE browser extension

### WCAG 2.1 Level AA Compliance

**Perceivable:**
- ✅ Text alternatives for images
- ✅ Color not sole means of conveying information
- ✅ Sufficient color contrast

**Operable:**
- ✅ Keyboard accessible
- ✅ No keyboard traps
- ✅ Sufficient time for interactions

**Understandable:**
- ✅ Readable text
- ✅ Predictable navigation
- ✅ Input assistance (labels, errors)

**Robust:**
- ✅ Valid HTML
- ✅ Compatible with assistive technologies

---

## Task 11.10: Nginx Proxy Verification ✅

### Test Steps

1. **Open Browser DevTools**
   - Press F12
   - Go to Network tab
   - Check "Preserve log"

2. **Monitor API Calls**
   - Login to the application
   - Navigate through different pages
   - Create a job
   - View job status
   - Access admin panel

3. **Verify All API Calls**
   - Filter Network tab by "XHR" or "Fetch"
   - Check each API request:
     - Request URL starts with `http://localhost:5173/api/`
     - NOT `http://localhost:8000/api/`
   - All requests go through nginx proxy

4. **Check Request Headers**
   - Click on any API request
   - Go to "Headers" tab
   - Verify proxy headers added by nginx:
     - `X-Real-IP`: Client IP
     - `X-Forwarded-For`: Client IP
     - `X-Forwarded-Proto`: http

5. **Check Response Headers**
   - Verify backend headers are preserved
   - CORS headers from backend (not nginx)
   - Content-Type: application/json

6. **Test SSE Proxy**
   - Navigate to job status page
   - Find SSE connection in Network tab
   - Request URL: `http://localhost:5173/api/v1/jobs/{id}/stream`
   - Content-Type: text/event-stream
   - Connection stays open (pending)

### Verification Checklist

- [ ] All API calls use `localhost:5173` (nginx)
- [ ] No direct calls to `localhost:8000` (backend)
- [ ] Proxy headers added by nginx
- [ ] Backend response headers preserved
- [ ] CORS headers from backend (not duplicated)
- [ ] SSE connections proxied correctly
- [ ] No 307 redirects (trailing slashes correct)
- [ ] Cookies sent with credentials: 'include'

### Expected API Calls

**Authentication:**
```
POST http://localhost:5173/api/v1/auth/login/
POST http://localhost:5173/api/v1/auth/register/
POST http://localhost:5173/api/v1/auth/logout/
POST http://localhost:5173/api/v1/auth/refresh/
GET  http://localhost:5173/api/v1/auth/me/
```

**Jobs:**
```
GET  http://localhost:5173/api/v1/jobs/
POST http://localhost:5173/api/v1/jobs/
GET  http://localhost:5173/api/v1/jobs/{id}/status/
GET  http://localhost:5173/api/v1/jobs/{id}/results/
GET  http://localhost:5173/api/v1/jobs/{id}/stream (SSE)
```

**Categories:**
```
GET  http://localhost:5173/api/v1/categories/
GET  http://localhost:5173/api/v1/categories/{id}/sources/
```

**Admin:**
```
GET  http://localhost:5173/api/v1/admin/results/
```

### Nginx Proxy Configuration

```nginx
location /api/ {
    proxy_pass http://backend:8000;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection 'upgrade';
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    
    # SSE specific
    proxy_buffering off;
    proxy_cache off;
    proxy_read_timeout 86400s;
}
```

---

## Automated Verification Script

Run this to verify API endpoints are accessible through nginx:

```bash
# Test health endpoint
curl -s http://localhost:5173/health
# Expected: "healthy"

# Test API proxy (should return 401 without auth)
curl -s http://localhost:5173/api/v1/auth/me/
# Expected: {"detail":"Not authenticated"}

# Test categories endpoint
curl -s http://localhost:5173/api/v1/categories/
# Expected: {"items":[...],"total":...}

# Verify no direct backend access from frontend
# All requests should go through nginx at :5173, not :8000
```

---

## Summary Checklist

### Task 11.5: Job Creation ✅
- [ ] Login works
- [ ] Dashboard loads
- [ ] Job creation form works
- [ ] Job created successfully
- [ ] Redirects to job status page
- [ ] Job appears in history

### Task 11.6: Admin Filtering ✅
- [ ] Admin login works
- [ ] Admin panel accessible
- [ ] Status filter works
- [ ] Category filter works
- [ ] City filter works
- [ ] Multiple filters work
- [ ] Clear filters works
- [ ] Sorting works
- [ ] Pagination works

### Task 11.7: SSE Updates ✅
- [ ] SSE connection established
- [ ] Real-time updates work
- [ ] Status changes without refresh
- [ ] Result count updates
- [ ] Data preserved during updates
- [ ] Polling fallback works

### Task 11.8: Mobile Responsive ✅
- [ ] Login page responsive
- [ ] Dashboard responsive
- [ ] Job status responsive
- [ ] Admin panel responsive
- [ ] No horizontal scroll
- [ ] Touch targets adequate
- [ ] Text readable

### Task 11.9: Accessibility ✅
- [ ] Keyboard navigation works
- [ ] Tab order logical
- [ ] Focus indicators visible
- [ ] Form labels present
- [ ] Color contrast sufficient
- [ ] No keyboard traps

### Task 11.10: Nginx Proxy ✅
- [ ] All API calls through nginx
- [ ] No direct backend calls
- [ ] Proxy headers added
- [ ] SSE proxied correctly
- [ ] No 307 redirects
- [ ] CORS headers correct

---

## Issues Found

Document any issues discovered during testing:

1. **Issue**: [Description]
   - **Severity**: Critical / High / Medium / Low
   - **Steps to Reproduce**: [Steps]
   - **Expected**: [Expected behavior]
   - **Actual**: [Actual behavior]
   - **Fix**: [Solution or workaround]

---

## Sign-Off

- [ ] All tasks completed (11.5-11.10)
- [ ] All verification checklists passed
- [ ] No critical issues found
- [ ] Ready for production deployment

**Tested By**: _________________  
**Date**: _________________  
**Environment**: Docker Production Build  
**Frontend**: http://localhost:5173 (nginx)  
**Backend**: http://localhost:8000 (FastAPI)
