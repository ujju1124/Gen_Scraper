# Google Maps Scraper Setup Guide

The Google Maps scraper is a separate Go-based service that provides high-quality data extraction. This guide will help you set it up for local development or production deployment.

## Overview

The Google Maps scraper is a standalone service that:
- Runs on port 8080 (backend) and 3001 (frontend)
- Provides HTTP API for job submission and result retrieval
- Uses Playwright for browser automation
- Supports SerpApi fallback for improved reliability
- Extracts 33+ data fields per business

## Prerequisites

- **Go 1.21+** - [Download](https://go.dev/dl/)
- **Node.js 18+** - [Download](https://nodejs.org/)
- **Docker Desktop** - [Download](https://www.docker.com/products/docker-desktop)
- **Git** - [Download](https://git-scm.com/downloads)

## Installation Steps

### 1. Clone the Google Maps Scraper

```bash
# From the Gen_Scraper root directory
git clone https://github.com/gosom/google-maps-scraper.git google-maps-scraper
cd google-maps-scraper
```

### 2. Install Go Dependencies

```bash
go mod download
```

### 3. Install Node.js Dependencies (Frontend)

```bash
cd frontend
npm install
cd ..
```

### 4. Configure Environment

```bash
# Copy the example environment file
cp .env.example .env
```

Edit `.env` and configure:

```env
# Database (SQLite for development, PostgreSQL for production)
DATABASE_URL=postgres://postgres:postgres@localhost:5432/gmapssaas

# Encryption key (auto-generated if not set)
ENCRYPTION_KEY=your-32-character-encryption-key

# Server address
ADDR=:8080

# SerpApi (optional but recommended for fallback)
SERPAPI_API_KEY=your_serpapi_key_here
```

**Getting SerpApi Key (Optional)**:
1. Sign up at [https://serpapi.com/](https://serpapi.com/)
2. Free tier: 100 searches/month
3. Copy your API key to `.env`

### 5. Start the Services

You need **3 separate terminal windows**:

#### Terminal 1: Backend Server

```bash
cd google-maps-scraper
.\start-dev.ps1
```

Wait for the message: `"Admin user created successfully"` then press **Ctrl+C once**.

#### Terminal 2: Worker Process

```bash
cd google-maps-scraper
.\start-worker.ps1
```

Wait for the message: `"scraper cycle started"`. Keep this terminal running.

#### Terminal 3: Frontend (Optional)

```bash
cd google-maps-scraper/frontend
npm run dev
```

Wait for: `"Local: http://localhost:3001/"`. Keep this terminal running.

### 6. Verify Installation

Test the API:

```bash
# Health check
curl http://localhost:8080/health

# Should return: {"status":"ok"}
```

## Integration with Gen_Scraper

The Gen_Scraper backend communicates with the Google Maps scraper via HTTP API. Ensure:

1. **Go scraper is running** on port 8080
2. **Gen_Scraper `.env` is configured**:
   ```env
   GO_SCRAPER_ENABLED=true
   GO_SCRAPER_BASE_URL=http://localhost:8080
   GO_SCRAPER_TIMEOUT=900
   ```

## Usage

### Via Gen_Scraper API

The Gen_Scraper backend automatically uses the Go scraper when available:

```python
import requests

response = requests.post(
    "http://localhost:8000/api/jobs",
    json={
        "scraper_type": "google_maps",
        "keyword": "hotels in Kathmandu",
        "geo_coordinates": "27.693444,85.281924",
        "max_results": 50,
        "extract_emails": True
    }
)
```

### Direct API Usage

You can also call the Go scraper directly:

```bash
curl -X POST http://localhost:8080/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "name": "test-job",
    "keywords": ["hotels in Kathmandu"],
    "lang": "en",
    "zoom": 14,
    "depth": 10,
    "lat": "27.693444",
    "lon": "85.281924",
    "radius": 5000,
    "max_time": 300
  }'
```

## Troubleshooting

### Port 8080 Already in Use

```bash
# Windows
netstat -ano | findstr :8080
taskkill /PID <PID> /F

# Or change port in .env
ADDR=:8081
```

### Worker Not Processing Jobs

```bash
# Check worker logs (Terminal 2)
# Look for "scraper cycle started"

# Restart worker
# Press Ctrl+C in Terminal 2
.\start-worker.ps1
```

### Database Connection Failed

```bash
# Stop services
.\stop-dev.ps1

# Remove old database
docker volume rm google-maps-scraper_postgres_data

# Restart
.\start-dev.ps1
```

### SerpApi Fallback Not Working

```bash
# Verify API key in .env
SERPAPI_API_KEY=your_key_here

# Restart worker after updating .env
```

### Frontend Not Loading

```bash
cd frontend

# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install

# Start dev server
npm run dev
```

## Stopping the Services

To stop all services:

```bash
# Press Ctrl+C in each terminal window (Terminal 1, 2, 3)

# Then run cleanup script
.\stop-dev.ps1
```

## Production Deployment

For production deployment:

1. **Use PostgreSQL** instead of SQLite
2. **Set strong encryption key** in `.env`
3. **Configure reverse proxy** (Nginx) for port 8080
4. **Use process manager** (systemd, PM2) for worker
5. **Enable HTTPS** with SSL certificates
6. **Set up monitoring** and logging
7. **Configure backups** for database

## Architecture

```
┌─────────────────┐
│  Gen_Scraper    │
│  (FastAPI)      │
└────────┬────────┘
         │ HTTP API
         ▼
┌─────────────────┐     ┌─────────────────┐
│  Go Scraper     │────▶│  PostgreSQL     │
│  Backend :8080  │     │  (Jobs/Results) │
└────────┬────────┘     └─────────────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────┐
│  Go Scraper     │────▶│  Playwright     │
│  Worker         │     │  (Browser)      │
└─────────────────┘     └─────────────────┘
         │
         ▼ (fallback)
┌─────────────────┐
│  SerpApi        │
│  (API)          │
└─────────────────┘
```

## Data Fields Extracted

The Go scraper extracts 33+ fields per business:

**Basic Info**: title, category, address, phone, website, email
**Location**: latitude, longitude, plus_code, complete_address
**Ratings**: review_rating, review_count, reviews_per_rating
**Media**: images, thumbnail, images_count
**Business**: opening_hours, price_range, status, description
**IDs**: place_id, data_id, cid
**Extra**: owner_name, timezone, user_reviews, about

## Support

For issues specific to the Google Maps scraper:
- Check worker logs (Terminal 2)
- Review backend logs (Terminal 1)
- Verify Docker is running
- Ensure ports 8080 and 3001 are available

For Gen_Scraper integration issues:
- Check Gen_Scraper logs: `docker-compose logs celery-worker`
- Verify `GO_SCRAPER_BASE_URL` in Gen_Scraper `.env`
- Test health endpoint: `curl http://localhost:8080/health`
