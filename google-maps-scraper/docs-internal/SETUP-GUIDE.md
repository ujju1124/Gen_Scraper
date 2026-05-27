# Complete Setup Guide - Step by Step

This guide will walk you through setting up and running the Google Maps Scraper from scratch. Follow each step carefully.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Starting the Application](#starting-the-application)
4. [Using the Application](#using-the-application)
5. [Stopping the Application](#stopping-the-application)
6. [Troubleshooting](#troubleshooting)
7. [Advanced Usage](#advanced-usage)

---

## Prerequisites

Before you start, you need to install these tools on your computer.

### 1. Docker Desktop

**What it's for**: Running PostgreSQL database

**Download**: https://www.docker.com/products/docker-desktop/

**Installation steps**:
1. Download Docker Desktop for Windows
2. Run the installer
3. Follow the installation wizard
4. Restart your computer if prompted
5. Open Docker Desktop
6. Wait for it to say "Docker Desktop is running"

**Verify installation**:
```powershell
docker --version
```

**Expected output**: `Docker version 24.x.x, build xxxxx`

---

### 2. Go (Golang)

**What it's for**: Running the backend server and worker

**Download**: https://go.dev/dl/

**Installation steps**:
1. Download the Windows installer (.msi file)
2. Run the installer
3. Follow the installation wizard
4. Default installation path is fine: `C:\Program Files\Go`

**Verify installation**:
```powershell
go version
```

**Expected output**: `go version go1.21.x windows/amd64`

---

### 3. Node.js

**What it's for**: Running the frontend

**Download**: https://nodejs.org/ (Download the LTS version)

**Installation steps**:
1. Download the Windows installer (.msi file)
2. Run the installer
3. Follow the installation wizard
4. Make sure "Add to PATH" is checked

**Verify installation**:
```powershell
node --version
npm --version
```

**Expected output**: 
```
v18.x.x
9.x.x
```

---

### 4. Git (Optional but recommended)

**What it's for**: Cloning the repository

**Download**: https://git-scm.com/download/win

**Installation steps**:
1. Download the installer
2. Run the installer
3. Use default settings

**Verify installation**:
```powershell
git --version
```

---

## Installation

### Step 1: Get the Code

**Option A: If you have Git**
```powershell
cd C:\Users\DELL\Desktop
git clone <repository-url>
cd google-maps-scraper
```

**Option B: If you downloaded a ZIP file**
1. Extract the ZIP file to `C:\Users\DELL\Desktop\google-maps-scraper`
2. Open PowerShell
3. Navigate to the folder:
```powershell
cd "C:\Users\DELL\Desktop\google-maps-scraper"
```

---

### Step 2: Install Go Dependencies

```powershell
go mod download
```

**What this does**: Downloads all the Go libraries the backend needs

**Expected output**: 
```
go: downloading github.com/...
go: downloading github.com/...
...
```

**Time**: 1-2 minutes

---

### Step 3: Install Frontend Dependencies

```powershell
cd frontend
npm install
```

**What this does**: Downloads all the JavaScript libraries the frontend needs

**Expected output**:
```
added 275 packages in 30s
```

**Time**: 1-3 minutes (depending on internet speed)

**Go back to project root**:
```powershell
cd ..
```

---

### Step 4: Install Playwright Browsers

Playwright needs to download browser binaries for scraping.

```powershell
go run github.com/playwright-community/playwright-go/cmd/playwright@latest install --with-deps chromium
```

**What this does**: Downloads Chromium browser for automation

**Expected output**:
```
Downloading Chromium...
✔ Chromium downloaded
```

**Time**: 2-5 minutes

**Size**: ~300 MB

---

## Starting the Application

Now that everything is installed, let's start the application!

### Step 1: Start Docker Desktop

1. Open Docker Desktop from Start menu
2. Wait for it to say "Docker Desktop is running"
3. You should see a green icon in the system tray

---

### Step 2: Start the Backend

Open PowerShell in the project root directory.

```powershell
cd "C:\Users\DELL\Desktop\google-maps-scraper"
```

**Run the startup script**:
```powershell
.\start-dev.ps1
```

**If you get a security error**:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.\start-dev.ps1
```

**What this script does**:
1. ✅ Checks if Docker is running
2. ✅ Starts PostgreSQL in Docker
3. ✅ Generates encryption key
4. ✅ Runs database migrations
5. ✅ Creates admin user
6. ✅ Starts backend server

**Expected output**:
```
Starting Google Maps Scraper Development Environment...

Checking Docker...
Docker is running

Starting PostgreSQL...
[+] Running 1/1
✔ Container google-maps-scraper-postgres-1 Started

Waiting for PostgreSQL to be ready...
PostgreSQL is ready

Generating encryption key...
Encryption key generated

Configuration saved to .env file

Running database migrations...
Applied 7 migration(s)

Creating admin user...
╔═══════════════════════════════════════════════════════════╗
║      Google Maps Scraper Pro - Admin User Management      ║
╚═══════════════════════════════════════════════════════════╝

Creating/updating user 'admin'...
New user created

╔═══════════════════════════════════════════════════════════╗
║              Credentials (SAVE THESE!)                    ║
╠═══════════════════════════════════════════════════════════╣
║  Username: admin                                          ║
║  Password: 1234#abcd                                      ║
╚═══════════════════════════════════════════════════════════╝

========================================
Development environment is ready!
========================================

Admin Dashboard: http://localhost:8080/admin
Username: admin
Password: 1234#abcd

Starting backend server...
Press Ctrl+C to stop the server

{"time":"2026-04-13T17:00:52.654Z","level":"INFO","msg":"starting server","addr":":8080"}
```

**✅ Backend is now running!**

**Keep this PowerShell window open!** The backend needs to keep running.

---

### Step 3: Start the Worker

Open a **NEW PowerShell window** (keep the backend running in the first one).

```powershell
cd "C:\Users\DELL\Desktop\google-maps-scraper"
.\start-worker.ps1
```

**What this does**: Starts the worker that processes scraping jobs

**Expected output**:
```
Starting Google Maps Scraper Worker...

Loaded: DATABASE_URL
Loaded: ENCRYPTION_KEY
Loaded: ADDR

Starting worker process...
Press Ctrl+C to stop the worker

{"time":"2026-04-13T17:01:00.123Z","level":"INFO","msg":"worker started"}
{"time":"2026-04-13T17:01:00.456Z","level":"INFO","msg":"waiting for jobs..."}
```

**✅ Worker is now running!**

**Keep this PowerShell window open too!**

---

### Step 4: Start the Frontend

Open a **THIRD PowerShell window**.

```powershell
cd "C:\Users\DELL\Desktop\google-maps-scraper\frontend"
npm run dev
```

**What this does**: Starts the React development server

**Expected output**:
```
> gmaps-scraper-frontend@1.0.0 dev
> vite

VITE v5.4.21  ready in 1240 ms

➜  Local:   http://localhost:3000/
➜  Network: use --host to expose
➜  press h + enter to show help
```

**✅ Frontend is now running!**

**Keep this PowerShell window open as well!**

---

### Step 5: Get Your API Key

1. Open your browser
2. Go to: http://localhost:8080/admin
3. Login with:
   - **Username**: `admin`
   - **Password**: `1234#abcd`
4. Click **"API Keys"** in the navigation
5. Click **"Generate New API Key"**
6. **Copy the API key** (it looks like: `gms_xxxxxxxxxxxxx...`)
7. **Save it somewhere safe!** You'll need it in the next step.

---

### Step 6: Configure the Frontend

1. Open your browser
2. Go to: http://localhost:3000
3. Click **"Settings"** in the navigation
4. Paste your API key from Step 5
5. Click **"Save API Key"**

**✅ Setup complete! You're ready to scrape!**

---

## Using the Application

### Creating Your First Scraping Job

1. **Go to the frontend**: http://localhost:3000
2. **Click "New Job"**
3. **Fill in the form**:
   - **Search Keyword**: `hotels in Kathmandu`
   - **Language**: `English`
   - **Max Depth**: `10` (this will get ~150-200 results)
   - Leave other fields as default for now
4. **Click "Submit Job"**

**What happens next**:
- Job is created with status "pending"
- Worker picks it up (status changes to "running")
- Browser opens and scrapes Google Maps
- Results are saved to database
- Status changes to "completed"

**Time**: 2-5 minutes depending on Max Depth

---

### Viewing Results

1. **Go to "Dashboard"** (home page)
2. **Find your job** in the list
3. **Click the eye icon** 👁️ to view details
4. **See the results**:
   - Business names
   - Addresses
   - Phone numbers
   - Ratings and reviews
   - Websites
   - Coordinates
   - And much more!
5. **Download JSON** for complete data

---

### Advanced Search Options

#### Search by Geographic Area

Want hotels between two cities? Use coordinates!

**Example: Hotels between Kathmandu and Pokhara**

1. **Keyword**: `hotels`
2. **Geographic Coordinates**: `27.96,84.65` (midpoint)
3. **Search Radius**: `50000` (50km radius)
4. **Max Depth**: `20`

#### Extract Email Addresses

Enable **"Extract Emails"** checkbox to crawl business websites and find email addresses.

**Note**: This makes scraping slower but gets valuable contact information.

#### Get Extended Reviews

Enable **"Extract Extended Reviews"** to get up to ~300 reviews per place instead of just a few.

**Note**: This significantly increases scraping time.

#### Fast Mode

Enable **"Fast Mode"** for faster scraping using HTTP requests instead of browser.

**Requirements**: Must provide geographic coordinates

**Trade-off**: Faster but less detailed data

---

## Stopping the Application

### Stop the Frontend

In the PowerShell window running the frontend:
1. Press `Ctrl+C`
2. Confirm with `Y` if prompted

---

### Stop the Worker

In the PowerShell window running the worker:
1. Press `Ctrl+C`

---

### Stop the Backend

In the PowerShell window running the backend:
1. Press `Ctrl+C`

---

### Stop PostgreSQL

```powershell
.\stop-dev.ps1
```

**Or manually**:
```powershell
docker compose -f docker-compose.saas.yaml down
```

**What this does**: Stops and removes the PostgreSQL container

**Note**: Your data is safe! It's stored in a Docker volume.

---

### Stop Docker Desktop

1. Right-click Docker icon in system tray
2. Click "Quit Docker Desktop"

---

## Troubleshooting

### Problem: "Docker is not running"

**Solution**:
1. Open Docker Desktop
2. Wait for it to fully start
3. Try again

---

### Problem: "Port 8080 already in use"

**Cause**: Another application is using port 8080

**Solution**:
```powershell
# Find what's using port 8080
netstat -ano | findstr :8080

# Kill the process (replace PID with the number from above)
taskkill /PID <PID> /F
```

---

### Problem: "Port 5432 already in use"

**Cause**: Another PostgreSQL instance is running

**Solution**:
1. Stop other PostgreSQL services
2. Or change the port in `docker-compose.saas.yaml`:
```yaml
ports:
  - "5433:5432"  # Use 5433 instead
```

Then update `.env`:
```
DATABASE_URL=postgres://postgres:postgres@localhost:5433/gmapssaas?sslmode=disable
```

---

### Problem: "Failed to connect to database"

**Check if PostgreSQL is running**:
```powershell
docker ps
```

**Should see**:
```
CONTAINER ID   IMAGE                  STATUS         PORTS
a1b2c3d4e5f6   postgres:18-alpine     Up 5 minutes   0.0.0.0:5432->5432/tcp
```

**If not running**:
```powershell
docker compose -f docker-compose.saas.yaml up -d postgres
```

---

### Problem: "Job stuck in pending status"

**Cause**: Worker is not running

**Solution**: Start the worker:
```powershell
.\start-worker.ps1
```

---

### Problem: "Frontend shows connection error"

**Check**:
1. Is backend running? (http://localhost:8080/api/v1/jobs should respond)
2. Is API key correct? (Check Settings page)
3. Is API key valid? (Check admin dashboard)

---

### Problem: "Playwright browser won't launch"

**Solution**: Reinstall Playwright browsers:
```powershell
go run github.com/playwright-community/playwright-go/cmd/playwright@latest install --with-deps chromium
```

---

### Problem: "Out of disk space"

**Check Docker disk usage**:
```powershell
docker system df
```

**Clean up**:
```powershell
docker system prune -a
```

**⚠️ Warning**: This removes all unused Docker data!

---

## Advanced Usage

### Running Multiple Workers

Want to process jobs faster? Run multiple workers!

**Open multiple PowerShell windows** and run:
```powershell
.\start-worker.ps1
```

Each worker will process jobs independently.

---

### Changing Backend Port

Edit `.env`:
```
ADDR=:8081
```

Restart backend.

Update frontend proxy in `frontend/vite.config.ts`:
```typescript
proxy: {
  '/api': {
    target: 'http://localhost:8081',
    changeOrigin: true,
  }
}
```

---

### Accessing PostgreSQL Directly

```powershell
docker exec -it google-maps-scraper-postgres-1 psql -U postgres -d gmapssaas
```

**Useful commands**:
```sql
-- List all tables
\dt

-- View jobs
SELECT job_id, keyword, status, result_count FROM jobs;

-- View results for a specific job
SELECT title, address, phone FROM results WHERE job_id = 'abc123';

-- Count total results
SELECT COUNT(*) FROM results;

-- Exit
\q
```

---

### Resetting Everything

**To start completely fresh**:

```powershell
# Stop everything
.\stop-dev.ps1

# Remove all data
docker compose -f docker-compose.saas.yaml down -v

# Delete .env file
Remove-Item .env

# Start fresh
.\start-dev.ps1
```

**⚠️ Warning**: This deletes ALL scraped data!

---

### Exporting Data

#### Export as JSON

Use the "Download JSON" button in the job details page.

#### Export as CSV (Manual)

Connect to PostgreSQL and export:
```sql
\copy (SELECT title, address, phone, review_rating FROM results WHERE job_id = 'abc123') TO 'C:\Users\DELL\Desktop\results.csv' CSV HEADER;
```

---

### Scheduling Jobs

Want to scrape automatically every day?

**Option 1: Windows Task Scheduler**
1. Create a PowerShell script that submits a job via API
2. Schedule it in Task Scheduler

**Option 2: Cron (if using WSL)**
```bash
# Edit crontab
crontab -e

# Add line (runs daily at 2 AM)
0 2 * * * curl -X POST http://localhost:8080/api/v1/scrape -H "X-API-Key: your_key" -d '{"keyword":"hotels in kathmandu","max_depth":10}'
```

---

## Summary

### Quick Start Commands

```powershell
# 1. Start backend
.\start-dev.ps1

# 2. Start worker (new window)
.\start-worker.ps1

# 3. Start frontend (new window)
cd frontend
npm run dev

# 4. Open browser
# http://localhost:8080/admin (get API key)
# http://localhost:3000 (use the app)
```

### Quick Stop Commands

```powershell
# Stop frontend: Ctrl+C in frontend window
# Stop worker: Ctrl+C in worker window
# Stop backend: Ctrl+C in backend window

# Stop PostgreSQL
.\stop-dev.ps1
```

---

## What's Running Where

| Component | URL/Port | Purpose |
|-----------|----------|---------|
| Frontend | http://localhost:3000 | Web interface |
| Backend API | http://localhost:8080/api/v1 | REST API |
| Admin Dashboard | http://localhost:8080/admin | Manage API keys |
| PostgreSQL | localhost:5432 | Database |
| Worker | (background) | Processes jobs |

---

## File Structure

```
google-maps-scraper/
├── cmd/                    # Command-line applications
│   └── gmapssaas/
│       ├── main.go         # Entry point
│       ├── cmdserve/       # Backend server
│       └── cmdworker/      # Worker process
├── api/                    # REST API code
├── admin/                  # Admin dashboard
├── gmaps/                  # Scraping logic
├── frontend/               # React frontend
│   ├── src/
│   │   ├── pages/          # UI pages
│   │   └── lib/api.ts      # API client
│   └── package.json
├── migrations/             # Database migrations
├── docker-compose.saas.yaml # Docker configuration
├── start-dev.ps1           # Backend startup script
├── start-worker.ps1        # Worker startup script
├── stop-dev.ps1            # Shutdown script
├── .env                    # Environment variables (auto-generated)
├── ARCHITECTURE.md         # How it works
├── DOCKER-EXPLAINED.md     # Docker guide
└── SETUP-GUIDE.md          # This file
```

---

## Next Steps

Now that you have everything running:

1. **Experiment with different searches**
   - Try different keywords
   - Use geographic coordinates
   - Adjust Max Depth

2. **Explore the data**
   - Download JSON files
   - Analyze ratings and reviews
   - Export to CSV for Excel

3. **Customize the frontend**
   - Add new features
   - Change the design
   - Add data visualizations

4. **Scale up**
   - Run multiple workers
   - Increase Max Depth
   - Schedule automated scraping

---

## Getting Help

If you encounter issues:

1. **Check the logs**
   - Backend: Look at the PowerShell window
   - Worker: Look at the worker window
   - PostgreSQL: `docker logs google-maps-scraper-postgres-1`

2. **Read the documentation**
   - `ARCHITECTURE.md` - How it works
   - `DOCKER-EXPLAINED.md` - Docker concepts
   - `SETUP-GUIDE.md` - This file

3. **Common issues**
   - See [Troubleshooting](#troubleshooting) section above

---

## Congratulations! 🎉

You now have a fully functional Google Maps scraper running on your computer!

Happy scraping! 🚀
