# 🗺️ Google Maps Scraper

A powerful Google Maps scraper with automatic SerpApi fallback for improved reliability. Extract business data including contact information, ratings, reviews, and more.

![Go](https://img.shields.io/badge/Go-1.21+-00ADD8?logo=go)
![React](https://img.shields.io/badge/React-18-61DAFB?logo=react)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-336791?logo=postgresql)

## ✨ Features

- 🔍 **Dual Scraping System**: Primary Playwright scraper + SerpApi fallback
- 🎯 **33+ Data Points**: Title, address, phone, ratings, reviews, coordinates, and more
- 🌐 **Modern Web UI**: React frontend with real-time job monitoring
- 📊 **Job Queue**: Reliable background processing with River
- 💾 **PostgreSQL Database**: Persistent storage with migration support
- 🔄 **Automatic Fallback**: Seamlessly switches to SerpApi when needed

## 📋 Prerequisites

Before you begin, ensure you have:

- **Docker Desktop** - [Download here](https://www.docker.com/products/docker-desktop)
- **Go 1.21+** - [Download here](https://go.dev/dl/)
- **Node.js 18+** - [Download here](https://nodejs.org/)
- **Git** - [Download here](https://git-scm.com/downloads)

## 🚀 Quick Start

### 1️⃣ Clone the Repository

```bash
git clone <your-repository-url>
cd google-maps-scraper
```

### 2️⃣ Install Dependencies

**Backend:**
```bash
go mod download
```

**Frontend:**
```bash
cd frontend
npm install
cd ..
```

### 3️⃣ Configure SerpApi (Optional but Recommended)

For the fallback feature to work, you need a SerpApi key:

1. Sign up at [https://serpapi.com/](https://serpapi.com/) (free tier: 100 searches/month)
2. Copy your API key
3. Open `.env` file and add your key:

```env
SERPAPI_API_KEY=your_api_key_here
```

> **Note:** The system works without this, but the fallback feature won't be available.

### 4️⃣ Start the Application

You need **3 separate terminal windows**:

**Terminal 1 - Backend Server:**
```bash
.\start-dev.ps1
```
Wait for: `"Admin user created successfully"` then press **Ctrl+C** once.

**Terminal 2 - Worker Process:**
```bash
.\start-worker.ps1
```
Wait for: `"scraper cycle started"`

**Terminal 3 - Frontend:**
```bash
cd frontend
npm run dev
```
Wait for: `"Local: http://localhost:3001/"`

### 5️⃣ Access the Application

Open your browser and navigate to:
```
http://localhost:3001
```

## 🎯 Usage

### Creating Your First Job

1. Click **"New Job"** in the navigation
2. Fill in the search parameters:
   - **Keyword**: What to search (e.g., "hotels", "restaurants")
   - **Geo Coordinates**: Latitude,Longitude (e.g., "27.693444,85.281924")
   - **Zoom**: Map zoom level (12-15 recommended)
   - **Max Depth**: Number of results to scroll (10-20 recommended)
   - **Radius**: Search radius in kilometers
3. Click **"Start Scraping"**
4. Monitor progress in the jobs list
5. View results when complete

### Example Search

Try this to test the system:
- **Keyword:** `hotels`
- **Geo Coordinates:** `27.693444,85.281924` (Kathmandu, Nepal)
- **Zoom:** `14`
- **Max Depth:** `10`
- **Radius:** `2`

## 🔄 Fallback System

The scraper uses a two-tier approach:

1. **Primary (Gosom)**: Playwright-based browser automation
   - Extracts 33+ data fields
   - Free and unlimited
   - Higher data quality

2. **Fallback (SerpApi)**: API-based scraping
   - Activates when primary fails or returns 0 results
   - 100 free searches/month
   - Guaranteed results

You'll see which scraper was used via a badge in the job details:
- 🔍 **Gosom Scraper** (Blue) - Primary scraper
- 🌐 **SerpApi Fallback** (Green) - Backup scraper

## 📊 Data Extracted

Each place includes:

**Basic Information:**
- Title, Category, Address
- Phone, Website, Email
- Place ID, Data ID

**Location:**
- Latitude, Longitude
- Plus Code, Complete Address
- Borough, Street, City, Postal Code

**Ratings & Reviews:**
- Overall Rating
- Review Count
- Reviews per Rating (1-5 stars)
- User Reviews with descriptions

**Additional:**
- Opening Hours
- Popular Times
- Price Range
- Photos & Thumbnails
- Service Options

## 🛑 Stopping the Application

To stop all services:

```bash
# Press Ctrl+C in each terminal window
# Then run:
.\stop-dev.ps1
```

## 🔧 Configuration

### Environment Variables

Edit `.env` file to configure:

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection | `postgres://postgres:postgres@localhost:5432/gmapssaas` |
| `ENCRYPTION_KEY` | Encryption key | Auto-generated |
| `ADDR` | Server address | `:8080` |
| `SERPAPI_API_KEY` | SerpApi key | Required for fallback |

### Scraper Settings

Adjust in the frontend:
- **Max Depth**: 1-50 (higher = more results, slower)
- **Timeout**: Job timeout in seconds (default: 300)
- **Fast Mode**: Use HTTP instead of browser (faster, less data)
- **Extra Reviews**: Extract additional reviews

## 📁 Project Structure

```
google-maps-scraper/
├── cmd/gmapssaas/       # Application entry point
├── api/                 # REST API
├── admin/               # Admin dashboard
├── gmaps/               # Core scraping logic
├── serpapi/             # SerpApi integration
├── rqueue/              # Job queue
├── scraper/             # Scraper manager
├── migrations/          # Database migrations
├── frontend/            # React application
├── .env                 # Configuration
├── start-dev.ps1       # Start backend
├── start-worker.ps1    # Start worker
└── stop-dev.ps1        # Stop services
```

## 🐛 Troubleshooting

### Docker Issues

**Problem:** "Docker is not running"
```bash
# Start Docker Desktop and wait for it to fully load
```

**Problem:** Port 5432 already in use
```bash
# Stop other PostgreSQL instances or change port in docker-compose.saas.yaml
```

### Backend Issues

**Problem:** Database connection failed
```bash
.\stop-dev.ps1
.\start-dev.ps1
```

**Problem:** Migration failed
```bash
.\stop-dev.ps1
docker volume rm google-maps-scraper-copy_postgres_data
.\start-dev.ps1
```

### Worker Issues

**Problem:** "Port 8080 already in use"
```
# This is expected - worker health endpoint conflicts with server
# Worker will still process jobs correctly
```

**Problem:** SerpApi fallback not working
```bash
# Check SERPAPI_API_KEY in .env
# Restart worker after updating .env
```

### Frontend Issues

**Problem:** Port 3000 in use
```
# Vite will automatically use port 3001
```

**Problem:** API key required
```
# Go to "API Settings" page in the frontend
# Enter any string for testing (or get real key from admin dashboard)
```

## 🔒 Security

- Change default admin password in production
- Keep `.env` file secure (contains API keys)
- Use HTTPS in production
- Implement rate limiting for public APIs
- Never commit API keys to Git

## 📚 API Documentation

### REST Endpoints

**Submit Job:**
```bash
POST /api/v1/scrape
Content-Type: application/json
X-API-Key: your-api-key

{
  "keyword": "hotels",
  "geo_coordinates": "27.693444,85.281924",
  "zoom": 14,
  "max_depth": 10,
  "radius": 2
}
```

**Get Job Status:**
```bash
GET /api/v1/jobs/{job_id}
X-API-Key: your-api-key
```

**List Jobs:**
```bash
GET /api/v1/jobs?state=completed&limit=20
X-API-Key: your-api-key
```

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `go test ./...`
5. Submit a pull request

## 📄 License

[Your License Here]

## 🆘 Support

If you encounter issues:

1. Check the troubleshooting section above
2. Review worker logs (Terminal 2) for errors
3. Ensure all prerequisites are installed
4. Verify Docker is running
5. Check that ports 8080 and 3001 are available

## 🎉 Success Checklist

- [ ] Docker Desktop installed and running
- [ ] Go 1.21+ installed
- [ ] Node.js 18+ installed
- [ ] Dependencies installed
- [ ] SerpApi key configured (optional)
- [ ] Backend server started
- [ ] Worker process started
- [ ] Frontend started
- [ ] Can access http://localhost:3001
- [ ] Can create and view jobs

---

**Built with ❤️ using Go, React, PostgreSQL, Playwright, and SerpApi**

For detailed documentation, see the `docs/` folder.
