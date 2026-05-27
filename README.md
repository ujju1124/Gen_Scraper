# Nepal Business Intelligence Platform

> Enterprise-grade data aggregation system for collecting and managing comprehensive business information across Nepal

[![Production Ready](https://img.shields.io/badge/status-production%20ready-brightgreen)]()
[![Data Sources](https://img.shields.io/badge/sources-4%20operational-blue)]()

---

## 🎯 Overview

The **Nepal Business Intelligence Platform** automatically collects, validates, and maintains business data from multiple trusted sources across Nepal. With intelligent deduplication, self-healing technology, and comprehensive data cleaning, the platform provides a reliable foundation for business directories, market research, and data enrichment services.

### Key Features

- ✅ **4 Operational Data Sources** - Google Maps, DirectoryOfNepal, NepalYP, Booking.com
- ✅ **30 Business Categories** - Hotels, restaurants, healthcare, education, and more
- ✅ **Geographic Coverage** - Multiple cities across Nepal
- ✅ **Self-Healing Technology** - Automatic adaptation to website changes
- ✅ **Intelligent Deduplication** - Multi-stage fuzzy matching and merging
- ✅ **Real-Time Validation** - 7-stage data cleaning pipeline

---

## 📊 Current Status

### Operational Data Sources (4)

| Source | Categories | Status |
|--------|------------|--------|
| **Google Maps** | All categories | ✅ Fully Operational |
| **DirectoryOfNepal** | Hotels, Restaurants, Pharmacies | ✅ Fully Operational |
| **NepalYP** | Hotels, Clinics/Doctors, Colleges, Banks, Travel Agents, Shopping Centers, Bakeries, Car Rentals, Schools | ✅ Fully Operational |
| **Booking.com** | Hotels | ✅ Fully Operational |

### Sources In Development (5)

| Source | Status | Challenge |
|--------|--------|-----------|
| **Agoda** | 🔧 Testing | Anti-bot measures, complex JavaScript |
| **Hostelworld** | 🔧 Testing | Dynamic content loading optimization |
| **OYO Rooms** | 🔧 Testing | Selector syntax errors |
| **Foodmandu** | 🔧 Testing | Angular SPA infinite scroll |
| **eSewa Hotels** | 🔧 Testing | Database selector corruption |

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
- 8GB RAM minimum
- 10GB free disk space

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd Gen_Scraper
   ```

2. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Start the platform**
   ```bash
   docker-compose up -d
   ```

4. **Access the application**
   - Frontend: http://localhost:5173
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

5. **Default credentials**
   - Email: `admin@example.com`
   - Password: Check `.env` file for `ADMIN_PASSWORD`
   - ⚠️ **Change default password immediately after first login**

---

## 📖 Core Features

### 1. Multi-Source Data Aggregation

Collects data from 4 operational sources with 5 more in development:
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

## 🔧 Development Roadmap

### Q3 2026
- ✨ Complete testing for Agoda, Hostelworld, Foodmandu
- ✨ Advanced search with filters
- ✨ Bulk data enrichment
- ✨ Scheduled scraping jobs

### Q4 2026
- ✨ Complete testing for OYO Rooms, eSewa Hotels
- ✨ Mobile application
- ✨ Advanced analytics dashboard
- ✨ Multi-language support

### 2027
- ✨ Additional international sources
- ✨ Regional expansion
- ✨ Real-time data streaming
- ✨ AI-powered data validation

---

## 🛡️ Security & Reliability

**Security**:
- Secure password hashing (bcrypt)
- Session management (HTTP-only cookies)
- Role-based access control
- Input validation and sanitization
- SQL injection prevention

**Reliability**:
- Containerized architecture
- Automatic health checks
- Service auto-restart
- Database backups
- Detailed logging

---

## 📞 Support

**Documentation**:
- Full product documentation: `PRODUCT_DOCUMENTATION.md`
- Source verification report: `SOURCE_VERIFICATION_COMPLETE.md`
- API documentation: http://localhost:8000/docs

**Technical Issues**:
- Check existing documentation files
- Review Docker logs: `docker-compose logs`
- Verify service health: `docker ps`

---

## 📄 License

Proprietary software. All rights reserved.

---

## 🎉 Project Highlights

- ✅ 4 operational data sources with 5 more in development
- ✅ Multiple cities covered across Nepal
- ✅ 30 business categories supported
- ✅ Self-healing technology for automatic adaptation
- ✅ Intelligent deduplication and merging
- ✅ Production-ready and stable

---

**Version**: 1.0.0  
**Last Updated**: May 18, 2026  
**Status**: Production Ready
