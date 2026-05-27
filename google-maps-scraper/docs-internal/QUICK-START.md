# 🚀 Quick Start Guide for Colleagues

This is a **5-minute setup guide** to get the Google Maps Scraper running on your machine.

## ✅ Prerequisites Checklist

Before starting, make sure you have:

- [ ] **Docker Desktop** installed and running
- [ ] **Go 1.21+** installed (`go version` to check)
- [ ] **Node.js 18+** installed (`node --version` to check)
- [ ] **Git** installed

## 📦 Step 1: Get the Code

```powershell
# Clone the repository
git clone <repository-url>
cd google-maps-scraper

# Install Go dependencies
go mod download

# Install frontend dependencies
cd frontend
npm install
cd ..
```

## 🔑 Step 2: Get SerpApi Key (Optional but Recommended)

The fallback feature requires a SerpApi key:

1. Go to https://serpapi.com/
2. Sign up (free - 100 searches/month)
3. Copy your API key
4. Open `.env` file and update:
   ```
   SERPAPI_API_KEY=your_key_here
   ```

**Note:** The system works without this, but fallback won't be available.

## 🎬 Step 3: Start Everything

Open **3 separate PowerShell terminals** in the project folder:

### Terminal 1: Backend
```powershell
.\start-dev.ps1
```
Wait for: `"Admin user created successfully"` then press **Ctrl+C** once.

### Terminal 2: Worker
```powershell
.\start-worker.ps1
```
Wait for: `"scraper cycle started"`

### Terminal 3: Frontend
```powershell
cd frontend
npm run dev
```
Wait for: `"Local: http://localhost:3001/"`

## 🌐 Step 4: Open the App

Open your browser and go to:
```
http://localhost:3001
```

## 🧪 Step 5: Test It

1. Click **"New Job"**
2. Fill in:
   - **Keyword:** `hotels`
   - **Geo Coordinates:** `27.693444,85.281924`
   - **Zoom:** `14`
   - **Max Depth:** `10`
3. Click **"Start Scraping"**
4. Watch the job complete!

## 🎯 What You Should See

- **Dashboard:** List of jobs
- **Job Details:** Results with place information
- **Scraper Badge:** Shows which scraper was used
  - 🔍 Blue = Main scraper (Gosom)
  - 🌐 Green = Fallback (SerpApi)

## 🛑 Stopping Everything

```powershell
# In each terminal, press Ctrl+C
# Then run:
.\stop-dev.ps1
```

## ❓ Common Issues

### "Docker is not running"
→ Start Docker Desktop and wait for it to fully load

### "Port already in use"
→ Stop other services or change ports in config

### "Database connection failed"
→ Run `.\stop-dev.ps1` then `.\start-dev.ps1` again

### "No API key" error in frontend
→ Go to "API Settings" page and enter any string (for testing)

## 📞 Need Help?

1. Check **README.md** for detailed documentation
2. Check **TROUBLESHOOTING** section in README
3. Look at worker logs (Terminal 2) for errors
4. Ask the team!

---

**That's it! You're ready to scrape Google Maps! 🎉**
