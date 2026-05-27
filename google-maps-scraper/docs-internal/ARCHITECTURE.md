# Google Maps Scraper - Architecture & How It Works

This document explains **exactly how the scraper works** - from submitting a job to getting results. Written in simple language with examples.

---

## Table of Contents

1. [Overview - The Big Picture](#overview---the-big-picture)
2. [Backend Architecture](#backend-architecture)
3. [How Scraping Works - Step by Step](#how-scraping-works---step-by-step)
4. [Frontend to Backend Connection](#frontend-to-backend-connection)
5. [Code Examples](#code-examples)
6. [Data Flow Diagram](#data-flow-diagram)

---

## Overview - The Big Picture

Imagine you want to find all hotels in Kathmandu. Here's what happens:

1. **You submit a job** through the web interface (frontend)
2. **Backend receives it** and saves it to a database queue
3. **Worker picks it up** and opens a real Chrome browser
4. **Browser goes to Google Maps** and searches "hotels in Kathmandu"
5. **Worker scrolls through results** and clicks each hotel
6. **Data is extracted** (name, address, phone, reviews, etc.)
7. **Results are saved** to the database
8. **You view the results** in the web interface

**Simple analogy**: It's like hiring a robot assistant who:
- Opens Google Maps on their computer
- Searches for what you asked
- Writes down all the information they find
- Gives you a neat report

---

## Backend Architecture

The backend has **4 main components**:

### 1. API Server (Port 8080)
**What it does**: Receives requests from the frontend

**Location**: `cmd/gmapssaas/cmdserve/cmd_serve.go`

**Responsibilities**:
- Accept job submissions from users
- Return job status and results
- Manage API keys for authentication
- Serve the admin dashboard

**Example**: When you click "Submit Job" in the frontend, it sends a request to:
```
POST http://localhost:8080/api/v1/scrape
```

### 2. PostgreSQL Database
**What it does**: Stores everything

**What's stored**:
- Job queue (pending, running, completed jobs)
- Scraped results (all the hotel data)
- User accounts and API keys
- Job history and logs

**Example**: When a job is created, a row is inserted:
```sql
INSERT INTO jobs (job_id, keyword, status, created_at) 
VALUES ('abc123', 'hotels in kathmandu', 'pending', NOW());
```

### 3. Worker Process
**What it does**: The actual scraper that does the work

**Location**: `cmd/gmapssaas/cmdworker/cmd_worker.go`

**Responsibilities**:
- Monitor the job queue for new jobs
- Launch browser and scrape Google Maps
- Extract data from each place
- Save results to database
- Update job status

**Example**: Worker checks every few seconds:
```
"Are there any pending jobs? Yes! Let me start scraping..."
```

### 4. Job Queue (River)
**What it does**: Manages the queue of scraping jobs

**How it works**:
- Jobs are added to a queue when submitted
- Workers pull jobs from the queue one at a time
- If a job fails, it can be retried
- Multiple workers can run simultaneously

**Example**: Like a restaurant kitchen:
- Orders (jobs) come in
- Cooks (workers) take orders from the queue
- Each cook works on one order at a time

---

## How Scraping Works - Step by Step

Let's follow a real example: **"Find hotels in Kathmandu"**

### Step 1: Job Submission

**Frontend sends**:
```json
{
  "keyword": "hotels in Kathmandu",
  "lang": "en",
  "max_depth": 10
}
```

**Backend receives** and creates a job:
```go
// In api/api.go
job := &Job{
    JobID:    generateUniqueID(),
    Keyword:  "hotels in Kathmandu",
    Status:   "pending",
    MaxDepth: 10,
}
db.Insert(job)
```

**Job is now in the queue** waiting for a worker.

---

### Step 2: Worker Picks Up Job

**Worker checks the queue**:
```go
// In cmd/gmapssaas/cmdworker/cmd_worker.go
job := queue.GetNextPendingJob()
if job != nil {
    job.Status = "running"
    db.Update(job)
    startScraping(job)
}
```

**Job status changes**: `pending` → `running`

---

### Step 3: Browser Launches

**Worker uses Playwright** (a browser automation tool):

```go
// In gmaps/job.go
browser := playwright.Chromium.Launch()
page := browser.NewPage()
```

**What happens**: A real Chrome browser window opens (you can't see it, it runs in the background).

---

### Step 4: Navigate to Google Maps

**Worker opens Google Maps**:
```go
url := "https://www.google.com/maps/search/hotels+in+Kathmandu"
page.Goto(url)
```

**What you'd see** (if the browser was visible):
- Google Maps loads
- Search results appear on the left side
- Map shows pins for each hotel

---

### Step 5: Scroll Through Results

**Worker scrolls to load more results**:

```go
// In gmaps/searchjob.go
for i := 0; i < maxDepth; i++ {
    // Scroll down the results panel
    page.Evaluate("document.querySelector('.results').scrollBy(0, 1000)")
    
    // Wait for new results to load
    time.Sleep(2 * time.Second)
}
```

**Why scroll?** Google Maps only shows ~20 results initially. Scrolling loads more.

**Example**:
- Scroll 1: 20 results
- Scroll 2: 40 results
- Scroll 3: 60 results
- ...and so on

---

### Step 6: Extract Place Links

**Worker collects all place links**:

```go
// Find all place links in the results
links := page.QuerySelectorAll("a[href*='/maps/place/']")

placeURLs := []string{}
for _, link := range links {
    href := link.GetAttribute("href")
    placeURLs = append(placeURLs, href)
}
```

**Result**: A list of URLs like:
```
https://www.google.com/maps/place/Hotel+Yak+%26+Yeti/@27.7172,85.3240...
https://www.google.com/maps/place/Kathmandu+Marriott+Hotel/@27.7172,85.3240...
...
```

---

### Step 7: Visit Each Place

**Worker clicks each hotel** (one by one):

```go
for _, url := range placeURLs {
    page.Goto(url)
    
    // Extract data from this place
    data := extractPlaceData(page)
    
    // Save to database
    db.Insert(data)
}
```

---

### Step 8: Extract Data from Each Place

**Worker reads the page** and extracts information:

```go
// In gmaps/place.go
func extractPlaceData(page Page) Place {
    return Place{
        Title:         page.TextContent("h1"),
        Address:       page.TextContent("[data-item-id='address']"),
        Phone:         page.TextContent("[data-item-id='phone']"),
        Website:       page.GetAttribute("a[data-item-id='authority']", "href"),
        Rating:        page.TextContent(".rating"),
        ReviewCount:   page.TextContent(".review-count"),
        Category:      page.TextContent(".category"),
        // ... 30+ more fields
    }
}
```

**What it extracts** (33+ fields):
- Basic info: name, address, phone, website
- Ratings: overall rating, review count, rating breakdown
- Location: latitude, longitude, plus code
- Business details: category, price range, hours
- Reviews: user reviews with text, ratings, photos
- Images: thumbnail and full image gallery
- And much more!

---

### Step 9: Save Results

**Each place is saved** to the database:

```go
result := PlaceResult{
    JobID:        job.JobID,
    Title:        "Hotel Yak & Yeti",
    Address:      "Durbar Marg, Kathmandu",
    Phone:        "01-4248999",
    Rating:       4.5,
    ReviewCount:  1234,
    Latitude:     27.7172,
    Longitude:    85.3240,
    // ... all other fields
}

db.Insert(result)
job.ResultCount++
```

---

### Step 10: Job Completes

**After all places are scraped**:

```go
job.Status = "completed"
job.CompletedAt = time.Now()
db.Update(job)

browser.Close()
```

**Job status changes**: `running` → `completed`

**You can now view results** in the frontend!

---

## Frontend to Backend Connection

### How They Communicate

The frontend (React) and backend (Go) talk using **HTTP requests** (like sending letters back and forth).

### API Endpoints

The backend exposes these URLs:

| Endpoint | Method | Purpose | Example |
|----------|--------|---------|---------|
| `/api/v1/scrape` | POST | Submit a new job | Create "hotels in Kathmandu" job |
| `/api/v1/jobs` | GET | List all jobs | Get all your jobs |
| `/api/v1/jobs/:id` | GET | Get job details | Get results for job #123 |
| `/api/v1/jobs/:id` | DELETE | Delete a job | Remove job #123 |

### Authentication

Every request needs an **API key** in the header:

```http
GET /api/v1/jobs
X-API-Key: gms_66f29510cef60c0f5018656312b820bebf956bef34e5624315735f5eb89e1234
```

**Why?** To make sure only authorized users can submit jobs.

### Example: Submitting a Job

**Frontend code** (`frontend/src/lib/api.ts`):

```typescript
// User clicks "Submit Job" button
const submitJob = async (keyword: string) => {
  // Get API key from localStorage
  const apiKey = localStorage.getItem('apiKey')
  
  // Send POST request to backend
  const response = await axios.post(
    'http://localhost:8080/api/v1/scrape',
    {
      keyword: keyword,
      lang: 'en',
      max_depth: 10
    },
    {
      headers: {
        'X-API-Key': apiKey
      }
    }
  )
  
  // Backend responds with job ID
  return response.data.job_id
}
```

**Backend code** (`api/api.go`):

```go
// Receive the request
func (s *Server) HandleScrape(w http.ResponseWriter, r *http.Request) {
    // 1. Check API key
    apiKey := r.Header.Get("X-API-Key")
    if !isValidAPIKey(apiKey) {
        http.Error(w, "Invalid API key", 401)
        return
    }
    
    // 2. Parse request body
    var req ScrapeRequest
    json.NewDecoder(r.Body).Decode(&req)
    
    // 3. Create job
    job := &Job{
        JobID:    generateID(),
        Keyword:  req.Keyword,
        Status:   "pending",
        MaxDepth: req.MaxDepth,
    }
    
    // 4. Save to database
    db.Insert(job)
    
    // 5. Add to job queue
    queue.Enqueue(job)
    
    // 6. Send response
    json.NewEncoder(w).Encode(map[string]string{
        "job_id": job.JobID,
        "status": "pending",
    })
}
```

**What happens**:
1. Frontend sends job details
2. Backend validates API key
3. Backend creates job in database
4. Backend adds job to queue
5. Backend responds with job ID
6. Frontend shows "Job submitted!"

---

### Example: Getting Job Results

**Frontend code**:

```typescript
// User clicks on a job to view results
const getJobResults = async (jobId: string) => {
  const apiKey = localStorage.getItem('apiKey')
  
  const response = await axios.get(
    `http://localhost:8080/api/v1/jobs/${jobId}`,
    {
      headers: {
        'X-API-Key': apiKey
      }
    }
  )
  
  return response.data
}
```

**Backend code**:

```go
func (s *Server) HandleGetJob(w http.ResponseWriter, r *http.Request) {
    // 1. Get job ID from URL
    jobID := chi.URLParam(r, "id")
    
    // 2. Fetch job from database
    job := db.GetJob(jobID)
    
    // 3. Fetch results
    results := db.GetResults(jobID)
    
    // 4. Send response
    json.NewEncoder(w).Encode(map[string]interface{}{
        "job_id":       job.JobID,
        "keyword":      job.Keyword,
        "status":       job.Status,
        "result_count": len(results),
        "results":      results,
    })
}
```

**Response** (what frontend receives):

```json
{
  "job_id": "abc123",
  "keyword": "hotels in Kathmandu",
  "status": "completed",
  "result_count": 18,
  "results": [
    {
      "title": "Hotel Yak & Yeti",
      "address": "Durbar Marg, Kathmandu",
      "phone": "01-4248999",
      "rating": 4.5,
      "review_count": 1234,
      "website": "https://www.yakandyeti.com",
      "latitude": 27.7172,
      "longitude": 85.3240
    },
    // ... 17 more hotels
  ]
}
```

---

## Code Examples

### Example 1: How Browser Automation Works

```go
// This is simplified pseudocode showing the concept

// 1. Launch browser
browser := playwright.Launch()
page := browser.NewPage()

// 2. Go to Google Maps
page.Goto("https://www.google.com/maps/search/hotels+in+Kathmandu")

// 3. Wait for results to load
page.WaitForSelector(".results")

// 4. Scroll to load more results
for i := 0; i < 10; i++ {
    page.Evaluate("document.querySelector('.results').scrollBy(0, 1000)")
    time.Sleep(2 * time.Second)
}

// 5. Get all place links
links := page.QuerySelectorAll("a[href*='/maps/place/']")

// 6. Visit each place
for _, link := range links {
    url := link.GetAttribute("href")
    page.Goto(url)
    
    // 7. Extract data
    title := page.TextContent("h1")
    address := page.TextContent("[data-item-id='address']")
    phone := page.TextContent("[data-item-id='phone']")
    
    // 8. Save to database
    db.Insert(Place{
        Title:   title,
        Address: address,
        Phone:   phone,
    })
}

// 9. Close browser
browser.Close()
```

---

### Example 2: Job Queue System

```go
// How the job queue works

// Backend: Add job to queue
func SubmitJob(keyword string) string {
    job := Job{
        ID:      generateID(),
        Keyword: keyword,
        Status:  "pending",
    }
    
    // Save to database
    db.Insert(job)
    
    // Add to queue
    queue.Enqueue(job)
    
    return job.ID
}

// Worker: Process jobs from queue
func WorkerLoop() {
    for {
        // Get next pending job
        job := queue.Dequeue()
        
        if job != nil {
            // Update status
            job.Status = "running"
            db.Update(job)
            
            // Do the scraping
            results := scrapeGoogleMaps(job.Keyword)
            
            // Save results
            for _, result := range results {
                db.Insert(result)
            }
            
            // Mark as complete
            job.Status = "completed"
            job.ResultCount = len(results)
            db.Update(job)
        }
        
        // Wait a bit before checking again
        time.Sleep(5 * time.Second)
    }
}
```

---

## Data Flow Diagram

```
┌─────────────┐
│   Browser   │  1. User opens http://localhost:3000
│  (Frontend) │
└──────┬──────┘
       │
       │ 2. User submits job: "hotels in Kathmandu"
       │
       ▼
┌─────────────────────────────────────────────────┐
│  POST /api/v1/scrape                            │
│  Headers: X-API-Key: gms_xxx                    │
│  Body: { keyword: "hotels in Kathmandu" }       │
└──────┬──────────────────────────────────────────┘
       │
       │ 3. Request reaches backend
       ▼
┌─────────────┐
│ API Server  │  4. Validates API key
│  (Port 8080)│  5. Creates job in database
└──────┬──────┘  6. Adds job to queue
       │         7. Returns job_id to frontend
       │
       ▼
┌─────────────┐
│ PostgreSQL  │  Job saved:
│  Database   │  - job_id: "abc123"
└──────┬──────┘  - status: "pending"
       │         - keyword: "hotels in Kathmandu"
       │
       │ 8. Worker checks for pending jobs
       ▼
┌─────────────┐
│   Worker    │  9. Picks up job "abc123"
│   Process   │  10. Updates status to "running"
└──────┬──────┘
       │
       │ 11. Launches Chrome browser
       ▼
┌─────────────┐
│  Playwright │  12. Opens Google Maps
│   Browser   │  13. Searches "hotels in Kathmandu"
└──────┬──────┘  14. Scrolls through results
       │         15. Clicks each hotel
       │         16. Extracts data
       │
       │ 17. For each hotel found:
       ▼
┌─────────────┐
│ PostgreSQL  │  Saves result:
│  Database   │  - title: "Hotel Yak & Yeti"
└──────┬──────┘  - address: "Durbar Marg"
       │         - phone: "01-4248999"
       │         - rating: 4.5
       │         - ... 30+ more fields
       │
       │ 18. After all hotels scraped:
       ▼
┌─────────────┐
│   Worker    │  19. Updates job status to "completed"
│   Process   │  20. Closes browser
└──────┬──────┘
       │
       │ 21. Frontend polls for updates
       ▼
┌─────────────┐
│   Browser   │  22. Shows results to user
│  (Frontend) │  23. User can view/download data
└─────────────┘
```

---

## Key Technologies Explained

### 1. Playwright
**What**: Browser automation library
**Why**: Allows code to control a real browser
**Like**: A robot that can click, scroll, and read web pages

### 2. PostgreSQL
**What**: Database system
**Why**: Stores jobs and results reliably
**Like**: A filing cabinet for all your data

### 3. River (Job Queue)
**What**: Job queue system
**Why**: Manages which jobs to process and when
**Like**: A to-do list that workers check

### 4. Chi Router
**What**: HTTP routing library
**Why**: Directs incoming requests to the right handler
**Like**: A receptionist directing visitors

### 5. React + TypeScript
**What**: Frontend framework
**Why**: Builds the user interface
**Like**: The face of the application users interact with

---

## Summary

**The entire process in one sentence**:

You submit a keyword → Backend saves it as a job → Worker opens a browser → Browser goes to Google Maps → Worker extracts data from each place → Results are saved → You view them in the UI.

**Key insight**: The scraper is just automating what a human would do manually - search Google Maps, click each result, and write down the information. But it does it much faster and more accurately!
