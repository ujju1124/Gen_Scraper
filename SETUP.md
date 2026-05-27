# 🚀 Gen_Scraper - Complete Setup Guide for Beginners

## Welcome! 👋

This guide will help you set up Gen_Scraper from scratch on a **completely fresh laptop**. We'll install everything you need step-by-step.

**Total Time:** About 45 minutes  
**Difficulty:** Beginner-friendly  
**Requirements:** Windows 10/11 laptop with internet connection

**What makes this easy:** Docker handles all the complex setup automatically! You just install the basic tools and Docker does the rest.

---

## 📋 What We'll Install

1. **Git** - To download the project
2. **Docker Desktop** - To run ALL services automatically (database, backend, frontend, scrapers)
3. **Python** - For running local scripts (optional)
4. **Node.js** - For local development (optional)
5. **Go** - For local development (optional)
6. **Gen_Scraper Project** - The actual application

**Note:** Items 3-5 are optional! Docker runs everything inside containers, so you technically only need Git and Docker. However, having Python/Node/Go installed is useful for local development and debugging.

---

# Part 1: Install Required Software (30-40 minutes)

## Step 1: Install Git (5 minutes)

**What is Git?** A tool to download and manage code from the internet.

### Installation Steps:

1. **Open your web browser** (Chrome, Edge, Firefox, etc.)

2. **Go to:** https://git-scm.com/downloads

3. **Click** the big "Download for Windows" button

4. **Wait** for the download to complete (git-installer.exe)

5. **Run the installer:**
   - Double-click the downloaded file
   - Click "Yes" if Windows asks for permission
   - Click "Next" on every screen (use default settings)
   - Click "Install"
   - Wait for installation to complete
   - Click "Finish"

6. **Verify Git is installed:**
   - Press `Windows Key + R`
   - Type `powershell` and press Enter
   - In the blue window that opens, type:
     ```powershell
     git --version
     ```
   - Press Enter
   - You should see something like: `git version 2.43.0`

✅ **Git is now installed!**

---

## Step 2: Install Docker Desktop (15 minutes + Restart)

**What is Docker?** A platform that runs all the services (database, cache, etc.) in containers.

### Installation Steps:

1. **Go to:** https://www.docker.com/products/docker-desktop

2. **Click** "Download for Windows"

3. **Wait** for download to complete (Docker Desktop Installer.exe - about 500MB)

4. **Run the installer:**
   - Double-click the downloaded file
   - Click "Yes" if Windows asks for permission
   - **IMPORTANT:** Make sure "Use WSL 2 instead of Hyper-V" is checked
   - Click "OK"
   - Wait for installation (this takes 5-10 minutes)

5. **Restart your computer:**
   - Click "Close and restart" when prompted
   - **IMPORTANT:** Your computer MUST restart for Docker to work

6. **After restart, start Docker Desktop:**
   - Find "Docker Desktop" in your Start Menu
   - Click to open it
   - Wait for Docker to start (you'll see a whale icon in your system tray)
   - **Wait until the whale icon stops animating** (this means Docker is ready)
   - This can take 2-3 minutes the first time

7. **Accept the Docker Service Agreement:**
   - A window will pop up asking you to accept terms
   - Click "Accept"

8. **Skip the tutorial:**
   - Click "Skip tutorial" if asked

9. **Verify Docker is running:**
   - Open PowerShell (Windows Key + R, type `powershell`, press Enter)
   - Type:
     ```powershell
     docker --version
     ```
   - Press Enter
   - You should see: `Docker version 24.x.x` or similar
   - Then type:
     ```powershell
     docker info
     ```
   - Press Enter
   - You should see lots of information about Docker

✅ **Docker Desktop is now installed and running!**

**Troubleshooting Docker:**
- If you get "WSL 2 installation is incomplete" error:
  1. Open PowerShell as Administrator (right-click PowerShell, select "Run as administrator")
  2. Type: `wsl --install`
  3. Press Enter and wait
  4. Restart your computer
  5. Start Docker Desktop again

---

## Step 3: Install Python (5 minutes)

**What is Python?** A programming language used for the backend API server.

### Installation Steps:

1. **Go to:** https://www.python.org/downloads/

2. **Click** the yellow "Download Python 3.12.x" button (or latest version)

3. **Wait** for download to complete (python-installer.exe)

4. **Run the installer:**
   - Double-click the downloaded file
   - **⚠️ VERY IMPORTANT:** Check the box that says "Add Python to PATH"
   - **⚠️ THIS IS CRITICAL - DON'T SKIP THIS!**
   - Click "Install Now"
   - Click "Yes" if Windows asks for permission
   - Wait for installation
   - Click "Close" when done

5. **Verify Python is installed:**
   - Open a NEW PowerShell window (close old one if open)
   - Type:
     ```powershell
     python --version
     ```
   - Press Enter
   - You should see: `Python 3.12.x` or similar
   - Then type:
     ```powershell
     pip --version
     ```
   - Press Enter
   - You should see: `pip 24.x from...`

✅ **Python is now installed!**

**Troubleshooting:**
- If you get "python is not recognized" error:
  - You forgot to check "Add Python to PATH"
  - Uninstall Python (Settings → Apps → Python → Uninstall)
  - Install again and CHECK the "Add Python to PATH" box

---

## Step 4: Install Node.js (5 minutes)

**What is Node.js?** A JavaScript runtime needed for the frontend web interface.

### Installation Steps:

1. **Go to:** https://nodejs.org/

2. **Click** the green button that says "LTS" (Long Term Support)
   - It will say something like "20.11.0 LTS"

3. **Wait** for download to complete (node-installer.msi)

4. **Run the installer:**
   - Double-click the downloaded file
   - Click "Next"
   - Accept the license agreement, click "Next"
   - Click "Next" (keep default location)
   - Click "Next" (keep default features)
   - Click "Next" (skip optional tools)
   - Click "Install"
   - Click "Yes" if Windows asks for permission
   - Wait for installation
   - Click "Finish"

5. **Verify Node.js is installed:**
   - Open a NEW PowerShell window
   - Type:
     ```powershell
     node --version
     ```
   - Press Enter
   - You should see: `v20.11.0` or similar
   - Then type:
     ```powershell
     npm --version
     ```
   - Press Enter
   - You should see: `10.2.4` or similar

✅ **Node.js is now installed!**

---

## Step 5: Install Go (5 minutes)

**What is Go?** A programming language used for the Google Maps scraper service.

### Installation Steps:

1. **Go to:** https://go.dev/dl/

2. **Click** the blue "Microsoft Windows" download button
   - Look for the one that says "go1.22.x.windows-amd64.msi"

3. **Wait** for download to complete (go-installer.msi)

4. **Run the installer:**
   - Double-click the downloaded file
   - Click "Next"
   - Click "Next" (keep default location)
   - Click "Install"
   - Click "Yes" if Windows asks for permission
   - Wait for installation
   - Click "Finish"

5. **Verify Go is installed:**
   - Open a NEW PowerShell window
   - Type:
     ```powershell
     go version
     ```
   - Press Enter
   - You should see: `go version go1.22.x windows/amd64`

✅ **Go is now installed!**

---

## 🚀 Alternative: Install Everything at Once (Advanced)

**Note:** This is an advanced method using package managers. If you prefer the manual installation above, skip this section.

If you want to install all software automatically using a single command, you can use **Chocolatey** (a Windows package manager):

### Installation Steps:

1. **Open PowerShell as Administrator:**
   - Press `Windows Key`
   - Type `powershell`
   - Right-click on "Windows PowerShell"
   - Select "Run as administrator"
   - Click "Yes" when Windows asks for permission

2. **Install Chocolatey (if not already installed):**
   ```powershell
   Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
   ```
   - Press Enter
   - Wait for installation (about 30 seconds)

3. **Install all required software at once:**
   ```powershell
   choco install git docker-desktop python nodejs golang -y
   ```
   - Press Enter
   - **This will take 10-15 minutes**
   - You'll see each software being downloaded and installed
   - Wait until you see "Chocolatey installed X/X packages"

4. **Restart your computer:**
   ```powershell
   shutdown /r /t 0
   ```
   - Press Enter
   - Your computer will restart immediately

5. **After restart, verify everything is installed:**
   - Open PowerShell (normal, not as administrator)
   - Run these commands one by one:
     ```powershell
     git --version
     docker --version
     python --version
     node --version
     go version
     ```
   - Each should show a version number

6. **Start Docker Desktop:**
   - Find "Docker Desktop" in Start Menu
   - Click to open
   - Wait for the whale icon to appear and stop animating

✅ **All software installed at once!**

**Pros of this method:**
- ✅ Faster - one command installs everything
- ✅ Automatic - no need to download installers manually
- ✅ Consistent - same versions every time

**Cons of this method:**
- ❌ Requires administrator access
- ❌ Less control over installation options
- ❌ Need to trust Chocolatey package manager

**If you used this method, skip to Part 2 below!**

---

## ✅ Part 1 Complete!

You now have all the required software installed:
- ✅ Git
- ✅ Docker Desktop (and it's running)
- ✅ Python
- ✅ Node.js
- ✅ Go


---

# Part 2: Download and Setup Gen_Scraper (10 minutes)

**Good News:** Docker handles all the complex setup automatically! You just need to download the project and configure your credentials.

## Step 6: Download the Project (2 minutes)

1. **Open PowerShell:**
   - Press `Windows Key + R`
   - Type `powershell`
   - Press Enter

2. **Create and navigate to a folder where you want to store the project:**
   ```powershell
   mkdir C:\Temp
   ```
   - Press Enter
   - This creates the Temp folder (if you get "already exists" error, that's OK)
   
   ```powershell
   cd C:\Temp
   ```
   - Press Enter
   - This moves you into the Temp folder

3. **Download the project from GitHub:**
   ```powershell
   git clone https://github.com/ujju1124/Gen_Scraper.git
   ```
   - Press Enter
   - Wait for download (about 30 seconds)
   - You should see: "Cloning into 'Gen_Scraper'..."

4. **Enter the project folder:**
   ```powershell
   cd Gen_Scraper
   ```
   - Press Enter

5. **Verify you're in the right place:**
   ```powershell
   dir
   ```
   - Press Enter
   - You should see folders like: backend, frontend, google-maps-scraper

✅ **Project downloaded!**

---

## Step 7: Configure the Environment (3 minutes)

1. **Create the configuration file:**
   ```powershell
   Copy-Item .env.example .env
   ```
   - Press Enter

2. **Open the configuration file in Notepad:**
   ```powershell
   notepad .env
   ```
   - Press Enter
   - Notepad will open with the file

3. **Find these two lines in the file:**
   ```
   ADMIN_PASSWORD=
   ADMIN_EMAIL=
   ```

4. **⚠️ IMPORTANT: Set YOUR OWN credentials (these are just examples):**
   ```
   ADMIN_PASSWORD=YourStrongPassword123!
   ADMIN_EMAIL=your.email@example.com
   ```
   
   **Security Notes:**
   - ❌ **DO NOT use `admin123`** - This is just an example in this guide!
   - ✅ **Use a strong password** with letters, numbers, and symbols
   - ✅ **Use your real email** if you want to receive notifications
   - ✅ **Remember these credentials** - you'll need them to login!
   - 🔒 **These credentials are ONLY stored in your local `.env` file**
   - 🔒 **The `.env` file is never uploaded to GitHub** (it's in .gitignore)

5. **Optional: Customize performance settings**
   
   The `.env.example` file includes detailed comments explaining all configuration options.
   You can customize settings like:
   - `CELERY_CONCURRENCY` - Number of parallel background tasks (default: 2)
   - `MAX_DETAIL_PAGES_PER_JOB` - How many detail pages to scrape (default: 2)
   - `DETAIL_PAGE_DELAY_MIN/MAX` - Delays between requests (default: 2000-4000ms)
   - `GO_SCRAPER_TIMEOUT` - Scraping timeout (default: 120 seconds)
   
   **For beginners:** The default values work well for most systems. You can adjust later!
   
   **For advanced users:** See `CONFIGURATION_GUIDE.md` for detailed tuning recommendations.

6. **Save and close:**
   - Click "File" → "Save"
   - Close Notepad

✅ **Configuration complete!**

---

## Step 8: Start Docker Services (5 minutes)

**What's happening?** Docker will download and start all the services (database, cache, backend, frontend, scrapers). It also automatically installs all dependencies (Python packages, Node modules, Go modules) inside the containers - you don't need to do anything manually!

**Important:** If you already have Docker running other containers on your laptop, that's perfectly fine! `docker-compose up -d` only starts the Gen_Scraper containers and won't affect your other containers.

1. **Make sure Docker Desktop is running:**
   - Look for the whale icon in your system tray (bottom-right of screen)
   - If you don't see it, open Docker Desktop from Start Menu
   - Wait until the whale icon stops animating

2. **Start all services:**
   ```powershell
   docker-compose up -d
   ```
   - Press Enter
   - **This will take 3-5 minutes the first time** (downloading images)
   - You'll see lots of text scrolling
   - Wait until you see "✔ Container gen_scraper-..." messages

3. **Wait 30 seconds for services to fully start:**
   ```powershell
   Start-Sleep -Seconds 30
   ```
   - Press Enter
   - Wait...

4. **Check that everything is running:**
   ```powershell
   docker-compose ps
   ```
   - Press Enter
   - You should see a table with services
   - **All services should show "Up" in the STATUS column**
   - You should see about 11 services running

✅ **Docker services are running!**

**Troubleshooting:**
- If you see "Error: Cannot connect to Docker daemon":
  - Docker Desktop is not running
  - Open Docker Desktop and wait for it to start
  - Try the command again

- If a service shows "Exit" instead of "Up":
  - Check the logs: `docker-compose logs [service-name]`
  - Most common issue: Database not ready yet
  - Solution: Wait 30 more seconds and check again

---

## Step 9: Verify Everything Works (3 minutes)

**Note:** Docker automatically handles all dependencies (Go modules, Node packages, Python packages) inside the containers. You don't need to install them manually! 🎉

Let's test that all services are responding:

1. **Test the Backend API:**
   ```powershell
   Invoke-WebRequest -Uri http://localhost:8000/docs -UseBasicParsing
   ```
   - Press Enter
   - Look for: `StatusCode        : 200`
   - If you see 200, it's working! ✅

2. **Test the Go Scraper:**
   ```powershell
   Invoke-WebRequest -Uri http://localhost:8080/health -UseBasicParsing
   ```
   - Press Enter
   - Look for: `StatusCode        : 200`
   - If you see 200, it's working! ✅

3. **Test the Frontend:**
   ```powershell
   Invoke-WebRequest -Uri http://localhost:5173 -UseBasicParsing
   ```
   - Press Enter
   - Look for: `StatusCode        : 200`
   - If you see 200, it's working! ✅

✅ **All services are working!**

---

# Part 3: Access and Use the Application (5 minutes)

## Step 10: Open the Application

1. **Open your web browser** (Chrome, Edge, Firefox, etc.)

2. **Go to:**
   ```
   http://localhost:5173
   ```

3. **You should see the Gen_Scraper login page!** 🎉

4. **Login with the credentials you set in Step 7:**
   - Email: The email you entered in `.env` (e.g., `your.email@example.com`)
   - Password: The password you entered in `.env` (e.g., `YourStrongPassword123!`)
   - **Note:** Use YOUR credentials, not the examples from this guide!

5. **Click "Login"**

6. **You should now see the dashboard!** 🎊

✅ **You're in! The application is ready to use!**

---

## Step 11: Test the Scraper (Optional - 2 minutes)

Let's create a test scraping job to make sure everything works:

1. **In the web interface (http://localhost:5173):**
   - Click "Create New Job" or "New Scrape" button
   - Select "Google Maps" as scraper type
   - Enter keyword: `hotels`
   - Enter location: `Kathmandu, Nepal` (or any location)
   - Set max results: `5`
   - Click "Start Scraping"

2. **Watch the job progress:**
   - You should see your job appear in the list
   - Status will change: Pending → Running → Completed
   - Wait 1-2 minutes for completion
   - Click on the job to see results!

✅ **Scraping works!**

---

# 🎉 Setup Complete!

## What You Can Do Now:

### Access Points:
- **Main Application:** http://localhost:5173
- **API Documentation:** http://localhost:8000/docs
- **Database Admin:** http://localhost:5050
  - Email: admin@admin.com
  - Password: admin

### Features:
- ✅ Create scraping jobs
- ✅ Monitor job progress
- ✅ View and export results
- ✅ Manage sources and categories
- ✅ Admin dashboard

---

# 📚 Daily Usage

## Starting the Application (After Setup)

Every time you want to use Gen_Scraper:

1. **Make sure Docker Desktop is running:**
   - Look for whale icon in system tray
   - If not running, open Docker Desktop from Start Menu

2. **Open PowerShell and run:**
   ```powershell
   cd C:\Temp\Gen_Scraper
   docker-compose up -d
   ```

3. **Wait 30 seconds, then open browser:**
   ```
   http://localhost:5173
   ```

**That's it!** Takes about 30 seconds.

---

## Stopping the Application

When you're done using Gen_Scraper:

1. **Open PowerShell and run:**
   ```powershell
   cd C:\Temp\Gen_Scraper
   docker-compose down
   ```

2. **Wait for services to stop**

**Done!** This frees up your computer's resources.

---

# 🐛 Troubleshooting

## Problem: "Docker is not running"

**Solution:**
1. Open Docker Desktop from Start Menu
2. Wait for the whale icon to appear and stop animating
3. Try your command again

---

## Problem: "Port already in use"

**Solution:**
```powershell
cd C:\Temp\Gen_Scraper
docker-compose restart
```

---

## Problem: "Cannot access http://localhost:5173"

**Solution:**
1. Check if services are running:
   ```powershell
   docker-compose ps
   ```
2. All should show "Up"
3. If not, restart:
   ```powershell
   docker-compose down
   docker-compose up -d
   ```

---

## Problem: "python is not recognized"

**Solution:**
1. You forgot to check "Add Python to PATH" during installation
2. Uninstall Python:
   - Settings → Apps → Python → Uninstall
3. Reinstall Python and CHECK "Add Python to PATH"

---

## Problem: Database connection errors

**Solution:**
```powershell
docker-compose restart postgres
Start-Sleep -Seconds 10
docker-compose restart backend
```

---

## Problem: npm install fails

**Solution:**
Try using cmd instead:
```powershell
cmd /c npm install
```

---

# 📊 What's Running?

When Gen_Scraper is running, these services are active:

| Service | Purpose | Port |
|---------|---------|------|
| **PostgreSQL** | Database | 5433 |
| **Redis** | Cache | 6379 |
| **Backend** | Python API | 8000 |
| **Frontend** | Web Interface | 5173 |
| **Worker** | Background Jobs | - |
| **Go Scraper 1-4** | Scraping Service | 8080-8083 |
| **PgAdmin** | Database Admin | 5050 |

---

# 🔐 Security Notes

**IMPORTANT - Read This:**

1. **Your credentials are customizable:**
   - ✅ The `.env` file contains YOUR passwords (set in Step 7)
   - ✅ You can use any email and password you want
   - ✅ The examples in this guide (`admin123`, `admin@example.com`) are just for demonstration
   - ⚠️ **Always use strong passwords in production!**

2. **Your .env file is safe:**
   - 🔒 The `.env` file is **never uploaded to GitHub**
   - 🔒 It's listed in `.gitignore` to prevent accidental commits
   - 🔒 Each user sets their own credentials locally
   - 🔒 Your passwords stay on your computer only

3. **Before using in production:**
   - Change `SECRET_KEY=` to a random 64-character string
   - Use a very strong admin password (20+ characters)
   - Consider using environment-specific .env files

4. **Never commit secrets to Git:**
   - ❌ Never edit `.env.example` with real passwords
   - ❌ Never remove `.env` from `.gitignore`
   - ✅ Always keep real credentials in `.env` only

---

# 📁 Project Structure

```
C:\Temp\Gen_Scraper\
├── backend/              # Python FastAPI backend
├── frontend/             # React frontend
├── google-maps-scraper/  # Go scraper service
├── docker-compose.yml    # Docker configuration
├── .env                  # Your configuration (passwords, etc.)
└── SETUP.md             # This file!
```

---

# ✅ Final Checklist

Make sure you completed everything:

- [ ] Git installed and verified
- [ ] Docker Desktop installed, restarted computer, and Docker is running
- [ ] Python installed with "Add to PATH" checked
- [ ] Node.js installed and verified
- [ ] Go installed and verified
- [ ] Project cloned to C:\Temp\Gen_Scraper
- [ ] .env file created and configured
- [ ] Docker services started (docker-compose up -d)
- [ ] All services showing "Up" status (about 11 containers)
- [ ] Backend responds at http://localhost:8000/docs
- [ ] Go scraper responds at http://localhost:8080/health
- [ ] Frontend responds at http://localhost:5173
- [ ] Can login to the application
- [ ] Can see the dashboard

---

# 🎊 Congratulations!

You've successfully set up Gen_Scraper from scratch!

You now have a fully functional web scraping system that can:
- Scrape data from Google Maps
- Store data in a database
- Display results in a web interface
- Export data for analysis

**Happy scraping! 🚀**

---

# 📞 Need More Help?

- **Check logs:** `docker-compose logs -f`
- **Restart everything:** `docker-compose down && docker-compose up -d`
- **View service status:** `docker-compose ps`
- **Stop everything:** `docker-compose down`

---


