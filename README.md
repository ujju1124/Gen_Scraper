# Nepal Business Intelligence Platform

> Enterprise-grade data aggregation system for collecting and managing comprehensive business information across Nepal

---

## 🎯 Overview

The **Nepal Business Intelligence Platform** automatically collects, validates, and maintains business data from multiple trusted sources across Nepal. With intelligent deduplication, self-healing technology, and comprehensive data cleaning, the platform provides a reliable foundation for business directories, market research, and data enrichment services.

### Key Features

- ✅ **Multi-Source Data Aggregation** - Google Maps, DirectoryOfNepal, NepalYP, Booking.com
- ✅ **30 Business Categories** - Hotels, restaurants, healthcare, education, and more
- ✅ **Geographic Coverage** - Multiple cities across Nepal
- ✅ **Self-Healing Technology** - Automatic adaptation to website changes
- ✅ **Intelligent Deduplication** - Multi-stage fuzzy matching and merging
- ✅ **Real-Time Validation** - 7-stage data cleaning pipeline

---

## 🏗️ Architecture

### Technology Stack

**Backend**:
- FastAPI (Python) - High-performance async API
- Celery - Distributed task processing
- PostgreSQL 15 - Enterprise database
- Redis 7 - Cache and queue
- Playwright - Browser automation

**Frontend**:
- React 18 - Modern UI
- TanStack Table - Advanced data tables
- Tailwind CSS - Utility-first styling

**Infrastructure**:
- Docker & Docker Compose
- Nginx - Reverse proxy
- GitHub Actions - CI/CD

### System Components

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Frontend  │────▶│   Backend   │────▶│  PostgreSQL │
│   (React)   │     │  (FastAPI)  │     │  (Database) │
└─────────────┘     └─────────────┘     └─────────────┘
                           │
                           ▼
                    ┌─────────────┐     ┌─────────────┐
                    │   Worker    │────▶│    Redis    │
                    │  (Celery)   │     │   (Queue)   │
                    └─────────────┘     └─────────────┘
```

---

## 🚀 Quick Start

### Prerequisites

- Docker Desktop
- Python 3.11+
- **Go 1.21+** (for Google Maps scraper)
- **Node.js 18+** (for Google Maps scraper frontend)
- 8GB RAM minimum
- 10GB free disk space

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd Gen_Scraper
   ```

2. **Set up Google Maps Scraper** (Required for Google Maps data collection)
   
   The Google Maps scraper source code is included in the repository:
   
   ```bash
   # Install Go dependencies
   cd google-maps-scraper
   go mod download
   
   # Install Node.js dependencies for frontend
   cd frontend
   npm install
   cd ../..
   
   # Configure environment
   cp google-maps-scraper/.env.example google-maps-scraper/.env
   # Edit .env and add SERPAPI_API_KEY (optional)
   ```
   
   📖 **See [GOOGLE_MAPS_SCRAPER_SETUP.md](./GOOGLE_MAPS_SCRAPER_SETUP.md) for detailed instructions**

3. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Start the platform**
   ```bash
   docker-compose up -d
   ```

5. **Start Google Maps Scraper** (3 separate terminals)
   
   **Terminal 1 - Backend:**
   ```bash
   cd google-maps-scraper
   .\start-dev.ps1
   # Wait for "Admin user created successfully" then Ctrl+C once
   ```
   
   **Terminal 2 - Worker:**
   ```bash
   cd google-maps-scraper
   .\start-worker.ps1
   # Keep running
   ```
   
   **Terminal 3 - Frontend (Optional):**
   ```bash
   cd google-maps-scraper/frontend
   npm run dev
   # Keep running
   ```

6. **Access the application**
   - Frontend: http://localhost:5173
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs
   - Google Maps Scraper UI: http://localhost:3001 (optional)

7. **Default credentials**
   - Email: `admin@example.com`
   - Password: Check `.env` file for `ADMIN_PASSWORD`
   - ⚠️ **Change default password immediately after first login**

---

## 📖 Core Features

### 1. Multi-Source Data Aggregation

Collects data from multiple sources:
- Handles different website structures automatically
- Extracts comprehensive business information
- Continues working even if individual sources fail

### 2. Intelligent Deduplication

Multi-stage deduplication strategy:
- **Within-Job**: Removes duplicates in same scraping session
- **Cross-Job**: Prevents duplicates across different sessions
- **Intelligent Merging**: Fuzzy matching with confidence scoring
- **Smart Field Selection**: Chooses most complete data from each source

### 3. Self-Healing Technology™

Automatic adaptation to website changes:
- Automatic failure detection
- Intelligent selector analysis using Playwright browser automation
- Confidence-based application
- Continuous learning and improvement

### 4. 7-Stage Data Cleaning

Rigorous data processing pipeline:
1. Raw data storage
2. Normalization (phone, URLs, ratings)
3. Within-job deduplication
4. Cross-job deduplication
5. Field validation
6. Completeness scoring
7. Database storage

### 5. Admin Dashboard

Comprehensive management interface:
- Searchable results table with all collected businesses
- Inline editing with instant save
- Bulk operations (approve/reject)
- Advanced filtering and export
- Self-healing monitoring dashboard

---

## 🎯 Use Cases

- **Business Directories** - Build comprehensive listings with auto-updates
- **Market Research** - Analyze business landscapes and trends
- **Lead Generation** - Extract contact information for sales
- **Tourism Platforms** - Power booking and discovery services
- **Local Search** - Enable category and location-based search
- **Data Enrichment** - Fill missing information in existing databases

---

## 🛡️ Security & Reliability

**Security**:
- Secure password hashing (bcrypt)
- Session management (HTTP-only cookies)
- Role-based access control
- Input validation and sanitization
- SQL injection prevention
- Rate limiting on authentication endpoints
- Security headers (CSP, X-Frame-Options, etc.)

**Reliability**:
- Containerized architecture
- Automatic health checks
- Service auto-restart
- Database backups
- Detailed logging

---

## 📞 Support

**Documentation**:
- API documentation: http://localhost:8000/docs
- Review Docker logs: `docker-compose logs`
- Verify service health: `docker ps`

---

## 📄 License

Proprietary software. All rights reserved.
