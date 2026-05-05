# Gen Scraper - Hotel Data Scraping Portal

[![CI/CD](https://github.com/YOUR_ORG/gen-scraper/actions/workflows/ci.yml/badge.svg)](https://github.com/YOUR_ORG/gen-scraper/actions/workflows/ci.yml)
[![Backend Coverage](https://codecov.io/gh/YOUR_ORG/gen-scraper/branch/main/graph/badge.svg?flag=backend)](https://codecov.io/gh/YOUR_ORG/gen-scraper)
[![Frontend Coverage](https://codecov.io/gh/YOUR_ORG/gen-scraper/branch/main/graph/badge.svg?flag=frontend)](https://codecov.io/gh/YOUR_ORG/gen-scraper)

A comprehensive web scraping portal for collecting and managing hotel data from multiple sources across Nepal.

---

## 📚 Documentation

**All project documentation has been organized into the `docs/` folder for easy navigation.**

**👉 [Start Here: Documentation Index](docs/INDEX.md)**

### Quick Links

- **🚀 Current Progress & Bulk Collection**: [docs/current-progress/](docs/current-progress/)
- **🐳 Docker Setup & Troubleshooting**: [docs/docker-setup/](docs/docker-setup/)
- **🕷️ Scraper Implementations**: [docs/scraper-implementations/](docs/scraper-implementations/)
- **📊 Phase Reports (1-7)**: [docs/phase-reports/](docs/phase-reports/)
- **⚙️ Feature Implementations**: [docs/feature-implementations/](docs/feature-implementations/)
- **🔧 Troubleshooting & Fixes**: [docs/troubleshooting/](docs/troubleshooting/)
- **🧪 Testing Reports**: [docs/testing-reports/](docs/testing-reports/)

---

## Features

### Phase 1-3 (Complete)
- ✅ User authentication and authorization
- ✅ Multi-source hotel scraping (Booking.com)
- ✅ Data cleaning and validation pipeline
- ✅ Admin panel with result management
- ✅ Export functionality (CSV, JSON)

### Phase 4A (Complete)
- ✅ Location display on job pages
- ✅ Source manager in admin panel
- ✅ Result validation workflow
- ✅ Filtered export with admin controls
- ✅ Retry failed jobs functionality

### Phase 4B (In Progress)
- 🚧 GitHub Actions CI/CD Pipeline
- ⏸️ OpenStreetMap/Overpass Geocoding
- ⏸️ Additional Scrapers (Agoda, TripAdvisor, eSewa, NepalYP)

---

## Tech Stack

### Backend
- **Framework**: FastAPI (Python 3.11)
- **Database**: PostgreSQL 15
- **Cache**: Redis 7
- **Task Queue**: Celery
- **Migrations**: Alembic
- **Testing**: pytest
- **Scraping**: Playwright, Camoufox

### Frontend
- **Framework**: React 18
- **Build Tool**: Vite
- **Styling**: Tailwind CSS
- **Testing**: Vitest
- **HTTP Client**: Axios

### DevOps
- **CI/CD**: GitHub Actions
- **Containerization**: Docker, Docker Compose
- **Deployment**: Blue-Green deployment
- **Monitoring**: Codecov, Slack notifications

---

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Node.js 20+ (for local frontend development)
- Python 3.11+ (for local backend development)

### Development Setup

1. **Clone the repository**
```bash
git clone https://github.com/YOUR_ORG/gen-scraper.git
cd gen-scraper
```

2. **Start services with Docker Compose**
```bash
docker-compose up --build -d
```

> **Note**: The `--build` flag ensures all services are built from the latest code, preventing stale image cache issues. This is especially important for the migrator service to include recent database migrations.

3. **Database migrations and seeding are automatic**

The migrator service runs automatically on startup and handles both migrations and seeding. No manual steps required!

4. **Access the application**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Default Credentials
- **Admin**: admin@example.com / admin123
- **User**: user@example.com / user123

---

## Testing

### Backend Tests
```bash
# Run all tests
docker-compose run --rm backend pytest tests/ -v

# Run with coverage
docker-compose run --rm backend pytest tests/ -v --cov=. --cov-report=term

# Run specific test file
docker-compose run --rm backend pytest tests/test_auth.py -v
```

**Coverage Target**: ≥85%

### Frontend Tests
```bash
# Run all tests
cd frontend && npm test -- --run

# Run with coverage
npm test -- --run --coverage

# Run in watch mode
npm test
```

**Coverage Target**: ≥75%

---

## CI/CD Pipeline

The project uses GitHub Actions for automated testing and deployment.

### Pipeline Stages
1. **Backend Tests** - pytest with PostgreSQL and Redis
2. **Frontend Tests** - Vitest with ESLint
3. **Build Docker** - Build and push images to Docker Hub
4. **Deploy Staging** - Auto-deploy to staging environment
5. **Deploy Production** - Manual approval required

### Required Secrets

The CI/CD pipeline requires 6 GitHub Secrets to be configured:
- `DOCKER_USERNAME` - Docker Hub username
- `DOCKER_PASSWORD` - Docker Hub access token
- `SSH_PRIVATE_KEY` - SSH key for server deployments
- `STAGING_HOST` - Staging server address
- `PRODUCTION_HOST` - Production server address
- `SLACK_WEBHOOK` - Slack notifications URL

**📖 Complete Setup Guide**: See [GitHub Secrets Configuration](docs/github_secrets.md) for detailed instructions on generating and configuring each secret.

---

## Project Structure

```
gen-scraper/
├── .github/
│   └── workflows/
│       └── ci.yml              # CI/CD pipeline
├── backend/
│   ├── alembic/                # Database migrations
│   ├── models/                 # SQLAlchemy models
│   ├── routers/                # FastAPI routes
│   ├── scrapers/               # Scraper implementations
│   ├── services/               # Business logic
│   ├── tasks/                  # Celery tasks
│   ├── tests/                  # Backend tests
│   ├── main.py                 # FastAPI application
│   └── requirements.txt        # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── components/         # React components
│   │   ├── pages/              # Page components
│   │   ├── services/           # API clients
│   │   └── App.jsx             # Main app component
│   ├── tests/                  # Frontend tests
│   └── package.json            # Node dependencies
├── docs/                       # Documentation
│   ├── ci_cd_pipeline.md       # CI/CD guide
│   └── github_secrets.md       # GitHub Secrets setup
├── docker-compose.yml          # Docker services
└── README.md                   # This file
```

---

## Documentation

- [CI/CD Pipeline](docs/ci_cd_pipeline.md) - Complete CI/CD setup and troubleshooting
- [GitHub Secrets Configuration](docs/github_secrets.md) - Step-by-step guide for configuring required secrets
- [Phase 4B Anti-Blocking Guide](PHASE4B_ANTI_BLOCKING_GUIDE.md) - Scraper anti-detection strategies
- [API Documentation](http://localhost:8000/docs) - Interactive API docs (when running)

---

## Scrapers

### Active Scrapers
- **Booking.com** (Camoufox) - International hotel listings

### Coming Soon (Phase 4B)
- **Agoda** (Camoufox) - AWAITING SELECTORS
- **TripAdvisor** (Camoufox) - AWAITING SELECTORS
- **eSewa Hotels** (Playwright) - AWAITING SELECTORS
- **NepalYP** (Playwright) - AWAITING SELECTORS

---

## Contributing

1. Create a feature branch: `git checkout -b feature/my-feature`
2. Make your changes
3. Run tests: `pytest` and `npm test`
4. Commit: `git commit -m "Add my feature"`
5. Push: `git push origin feature/my-feature`
6. Create a Pull Request

### Code Quality
- Backend: Follow PEP 8, use type hints
- Frontend: Follow ESLint rules, use PropTypes
- Tests: Maintain ≥85% backend, ≥75% frontend coverage
- Commits: Write clear, descriptive commit messages

---

## License

[Add your license here]

---

## Contact

- **Project Lead**: [Your Name]
- **Email**: [your.email@example.com]
- **Issues**: [GitHub Issues](https://github.com/YOUR_ORG/gen-scraper/issues)

---

**Last Updated**: April 29, 2026  
**Version**: Phase 4B (In Progress)
