# 🔧 Gen_Scraper Configuration Guide

## Overview

This guide explains all configuration options in the `.env` file and how to customize Gen_Scraper for your system and requirements.

---

## 📋 Quick Start

1. **Copy the template:**
   ```bash
   cp .env.example .env
   ```

2. **Set required values:**
   - `ADMIN_PASSWORD` - Your admin password
   - `ADMIN_EMAIL` - Your admin email
   - `SECRET_KEY` - Random 64+ character string

3. **Adjust performance settings** based on your system (see below)

4. **Start the application:**
   ```bash
   docker-compose up -d
   ```

---

## 🎯 Configuration Categories

### 1. Application Settings

#### `ENV`
- **Purpose:** Environment mode
- **Options:** `development`, `staging`, `production`
- **Default:** `development`
- **Recommendation:** Use `production` for live deployments

#### `SECRET_KEY`
- **Purpose:** Encryption key for sessions and security
- **Format:** Random 64+ character string
- **Generate with:**
  ```bash
  python -c "import secrets; print(secrets.token_hex(64))"
  ```
- **⚠️ CRITICAL:** Must be unique and secret in production!

---

### 2. Database Configuration

#### `DATABASE_URL`
- **Purpose:** PostgreSQL connection string
- **Format:** `postgresql://username:password@host:port/database`
- **Docker:** `postgresql://scraper:scraper_pass@postgres:5432/scraper_db`
- **Local:** `postgresql://scraper:scraper_pass@localhost:5432/scraper_db`

#### `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`
- **Purpose:** Database credentials used by Docker containers
- **Default:** `scraper_db`, `scraper`, `scraper_pass`
- **Recommendation:** Change password in production

---

### 3. Redis & Celery (Background Jobs)

#### `REDIS_URL`
- **Purpose:** Redis connection for caching and task queue
- **Docker:** `redis://redis:6379/0`
- **Local:** `redis://localhost:6379/0`

#### `CELERY_CONCURRENCY`
- **Purpose:** Number of parallel background tasks
- **Impact:** Higher = more parallel jobs, more CPU/RAM usage

**Recommendations by System:**

| System Type | CPU Cores | RAM | Recommended Value |
|-------------|-----------|-----|-------------------|
| Low-end laptop | 2-4 | 4-8 GB | 1-2 |
| Mid-range laptop | 4-8 | 8-16 GB | 2-4 |
| High-end laptop | 8+ | 16+ GB | 4-8 |
| Production server | 16+ | 32+ GB | 8-16 |

**Formula:** `(CPU cores - 1)` or `(CPU cores - 2)` for production

---

### 4. Scraper Settings

#### `MOCK_MODE`
- **Purpose:** Use fake data for testing
- **Options:** `true` (fake data), `false` (real scraping)
- **Use case:** Testing without making real web requests

---

### 5. Go Scraper Microservice

#### `GO_SCRAPER_URL`
- **Purpose:** URL of the Go scraper service
- **Docker:** `http://go_scraper:8080`
- **Local:** `http://localhost:8080`

#### `GO_SCRAPER_API_KEY`
- **Purpose:** Authentication key for Go scraper
- **Generate with:**
  ```bash
  python -c "import secrets; print('gms_' + secrets.token_hex(32))"
  ```
- **⚠️ IMPORTANT:** Change from default in production!

#### `GO_SCRAPER_ENABLED`
- **Purpose:** Enable/disable Go scraper
- **Options:** `true`, `false`
- **Use case:** Disable for maintenance or testing

#### `GO_SCRAPER_TIMEOUT`
- **Purpose:** Maximum time to wait for scraping job (seconds)
- **Impact:** Higher = can handle larger jobs, but slower failure detection

**Recommendations by Job Size:**

| Job Size | Results | Recommended Timeout |
|----------|---------|---------------------|
| Small | 1-20 | 60-120 seconds |
| Medium | 20-100 | 120-240 seconds |
| Large | 100-500 | 240-600 seconds |
| Very Large | 500+ | 600-1200 seconds |

#### `GO_SCRAPER_POLL_INTERVAL`
- **Purpose:** How often to check job status (seconds)
- **Impact:** Lower = faster updates, more API calls

**Recommendations:**

| Polling Speed | Interval | Use Case |
|---------------|----------|----------|
| Fast | 2-3 seconds | Real-time monitoring |
| Balanced | 3-5 seconds | Normal use |
| Slow | 5-10 seconds | Reduce API load |

---

### 6. Detail Page Scraping Configuration

These settings control how much detailed information is scraped from each result.

#### `MAX_DETAIL_PAGES_PER_JOB`
- **Purpose:** Maximum number of detail pages to scrape per job
- **Impact:** Higher = more data, longer scraping time, more resources

**Recommendations by Use Case:**

| Use Case | Recommended Value | Scraping Time (approx) |
|----------|-------------------|------------------------|
| Testing/Development | 2-5 | 10-30 seconds |
| Quick overview | 10-20 | 30-90 seconds |
| Standard scraping | 20-50 | 1-3 minutes |
| Comprehensive data | 50-100 | 3-7 minutes |
| Maximum data | 100-500 | 7-30 minutes |
| Unlimited | 999999 | ⚠️ Use with caution! |

**⚠️ WARNING:** Very high values can:
- Take a long time to complete
- Use significant system resources
- Risk rate limiting or IP blocks
- Fill up your database quickly

#### `DETAIL_PAGE_DELAY_MIN` and `DETAIL_PAGE_DELAY_MAX`
- **Purpose:** Delay between detail page requests (milliseconds)
- **Impact:** Higher = more polite, slower scraping, less risk of blocking

**Recommendations by Strategy:**

| Strategy | MIN (ms) | MAX (ms) | Risk Level | Speed |
|----------|----------|----------|------------|-------|
| Polite/Safe | 2000-3000 | 3000-5000 | Low | Slow |
| Balanced | 1000-2000 | 2000-4000 | Medium | Medium |
| Aggressive | 500-1000 | 1000-2000 | High | Fast |

**⚠️ WARNING:** Too low delays may:
- Trigger rate limiting
- Get your IP blocked
- Violate terms of service
- Cause incomplete data

**💡 TIP:** Random delays (MIN to MAX) make scraping look more human-like

---

### 7. Admin User Configuration

#### `ADMIN_PASSWORD`
- **Purpose:** Password for the admin user
- **⚠️ CRITICAL:** Use a STRONG password!
- **Requirements:**
  - Minimum 12 characters (20+ recommended)
  - Mix of uppercase, lowercase, numbers, symbols
  - NOT a common word or pattern
- **Examples:**
  - ❌ BAD: `admin123`, `password`, `12345678`
  - ✅ GOOD: `MyStr0ng!P@ssw0rd#2026`, `Xk9$mP2#vL8@qR5!`

#### `ADMIN_EMAIL`
- **Purpose:** Email address for the admin user
- **Format:** Valid email address
- **Use case:** Login, notifications, password reset

---

### 8. Monitoring & Error Tracking

#### `SENTRY_DSN`
- **Purpose:** Sentry error tracking integration
- **Format:** Sentry DSN URL
- **Get from:** https://sentry.io/
- **Use case:** Track errors in production
- **Leave empty:** To disable error tracking

---

### 9. Frontend Configuration

#### `FRONTEND_URL`
- **Purpose:** URL where frontend is hosted
- **Default:** `http://localhost:5173`
- **Production:** Your domain (e.g., `https://scraper.yourcompany.com`)

#### `VITE_API_URL`
- **Purpose:** Backend API URL used by frontend
- **Default:** `http://localhost:8000`
- **Production:** Your API domain (e.g., `https://api.yourcompany.com`)

---

### 10. Email Configuration (Optional)

Configure SMTP to send email notifications.

#### `SMTP_HOST`
- **Purpose:** SMTP server hostname
- **Gmail:** `smtp.gmail.com`
- **Outlook:** `smtp.office365.com`
- **Custom:** Your SMTP server

#### `SMTP_PORT`
- **Purpose:** SMTP server port
- **Common ports:**
  - `587` - TLS (recommended)
  - `465` - SSL
  - `25` - Unencrypted (not recommended)

#### `SMTP_USER` and `SMTP_PASSWORD`
- **Purpose:** SMTP authentication credentials
- **Gmail:** Use App Password (not regular password)
  1. Enable 2-factor authentication
  2. Generate App Password: https://myaccount.google.com/apppasswords
  3. Use the 16-character app password

#### `SMTP_FROM_EMAIL`
- **Purpose:** Email address shown as sender
- **Example:** `noreply@yourcompany.com`

---

### 11. Data Retention

#### `RAW_RESULTS_RETENTION_DAYS`
- **Purpose:** Days to keep raw scraping results before cleanup
- **Impact:** Higher = more storage used

**Recommendations:**

| Use Case | Recommended Value |
|----------|-------------------|
| Short-term projects | 30 days |
| Standard use | 90 days |
| Long-term analysis | 180-365 days |
| Permanent storage | 999999 (⚠️ database will grow large) |

---

## 🎛️ Performance Tuning Presets

### Low-End System (2-4 CPU cores, 4-8 GB RAM)

```env
CELERY_CONCURRENCY=1
MAX_DETAIL_PAGES_PER_JOB=2
GO_SCRAPER_TIMEOUT=120
GO_SCRAPER_POLL_INTERVAL=5
DETAIL_PAGE_DELAY_MIN=2000
DETAIL_PAGE_DELAY_MAX=4000
```

**Best for:** Personal laptop, testing, development

---

### Mid-Range System (4-8 CPU cores, 8-16 GB RAM)

```env
CELERY_CONCURRENCY=2-4
MAX_DETAIL_PAGES_PER_JOB=20
GO_SCRAPER_TIMEOUT=240
GO_SCRAPER_POLL_INTERVAL=3
DETAIL_PAGE_DELAY_MIN=1000
DETAIL_PAGE_DELAY_MAX=3000
```

**Best for:** Standard laptop, small business, moderate scraping

---

### High-End System (8+ CPU cores, 16+ GB RAM)

```env
CELERY_CONCURRENCY=4-8
MAX_DETAIL_PAGES_PER_JOB=50-100
GO_SCRAPER_TIMEOUT=300
GO_SCRAPER_POLL_INTERVAL=2
DETAIL_PAGE_DELAY_MIN=500
DETAIL_PAGE_DELAY_MAX=2000
```

**Best for:** Workstation, production server, heavy scraping

---

### Production Server (16+ CPU cores, 32+ GB RAM)

```env
ENV=production
SECRET_KEY=<generate-unique-64-char-string>
CELERY_CONCURRENCY=8-16
MAX_DETAIL_PAGES_PER_JOB=100-500
GO_SCRAPER_TIMEOUT=600
GO_SCRAPER_POLL_INTERVAL=2
DETAIL_PAGE_DELAY_MIN=1000
DETAIL_PAGE_DELAY_MAX=2000
SENTRY_DSN=<your-sentry-dsn>
RAW_RESULTS_RETENTION_DAYS=180
```

**Best for:** Enterprise, high-volume scraping, multiple users

---

## 🔒 Security Best Practices

### 1. Strong Passwords
- ✅ Use 20+ character passwords
- ✅ Mix uppercase, lowercase, numbers, symbols
- ❌ Never use `admin123`, `password`, etc.

### 2. Unique Keys
- ✅ Generate unique `SECRET_KEY` for each environment
- ✅ Generate unique `GO_SCRAPER_API_KEY`
- ❌ Never reuse keys across environments

### 3. Environment Separation
- ✅ Different `.env` for development, staging, production
- ✅ Different database credentials per environment
- ❌ Never use production credentials in development

### 4. File Protection
- ✅ `.env` is in `.gitignore`
- ✅ Never commit `.env` to Git
- ✅ Restrict file permissions: `chmod 600 .env` (Linux/Mac)

### 5. Production Checklist
- [ ] `ENV=production`
- [ ] Strong `SECRET_KEY` (64+ chars)
- [ ] Strong `ADMIN_PASSWORD` (20+ chars)
- [ ] Unique `GO_SCRAPER_API_KEY`
- [ ] Changed database password
- [ ] Configured `SENTRY_DSN`
- [ ] Configured email (SMTP)
- [ ] Set appropriate retention days
- [ ] Tested backup and restore

---

## 🐛 Troubleshooting

### Problem: "Database connection failed"
**Solution:** Check `DATABASE_URL` matches your setup:
- Docker: Use `postgres` as host
- Local: Use `localhost` as host

### Problem: "Redis connection failed"
**Solution:** Check `REDIS_URL` matches your setup:
- Docker: Use `redis` as host
- Local: Use `localhost` as host

### Problem: "Scraping is too slow"
**Solutions:**
- Increase `CELERY_CONCURRENCY`
- Decrease `DETAIL_PAGE_DELAY_MIN` and `DETAIL_PAGE_DELAY_MAX`
- Decrease `GO_SCRAPER_POLL_INTERVAL`
- ⚠️ Be careful not to trigger rate limiting!

### Problem: "System is using too much CPU/RAM"
**Solutions:**
- Decrease `CELERY_CONCURRENCY`
- Decrease `MAX_DETAIL_PAGES_PER_JOB`
- Increase delays between requests

### Problem: "Getting rate limited or blocked"
**Solutions:**
- Increase `DETAIL_PAGE_DELAY_MIN` and `DETAIL_PAGE_DELAY_MAX`
- Decrease `MAX_DETAIL_PAGES_PER_JOB`
- Use proxy or VPN
- Spread scraping over longer time period

---

## 📊 Monitoring Your Configuration

### Check Current Settings

```bash
# View your current configuration (without secrets)
docker-compose config
```

### Monitor Resource Usage

```bash
# Check Docker container resource usage
docker stats

# Check specific service logs
docker-compose logs -f backend
docker-compose logs -f go_scraper
docker-compose logs -f worker
```

### Database Size

```bash
# Check database size
docker-compose exec postgres psql -U scraper -d scraper_db -c "SELECT pg_size_pretty(pg_database_size('scraper_db'));"
```

---

## 🎓 Advanced Tips

### 1. Environment-Specific Configs

Create multiple env files:
- `.env.development`
- `.env.staging`
- `.env.production`

Load with: `docker-compose --env-file .env.production up -d`

### 2. Dynamic Scaling

Adjust `CELERY_CONCURRENCY` based on load:
```bash
# Scale workers dynamically
docker-compose up -d --scale worker=4
```

### 3. Performance Testing

Test different configurations:
1. Start with conservative settings
2. Monitor resource usage
3. Gradually increase performance settings
4. Find optimal balance for your system

### 4. Cost Optimization

For cloud deployments:
- Lower `CELERY_CONCURRENCY` = smaller instance size
- Higher delays = less bandwidth usage
- Lower `MAX_DETAIL_PAGES_PER_JOB` = faster jobs, less storage

---

## ✅ Configuration Checklist

Before going live, verify:

- [ ] Copied `.env.example` to `.env`
- [ ] Set strong `ADMIN_PASSWORD`
- [ ] Set valid `ADMIN_EMAIL`
- [ ] Generated unique `SECRET_KEY`
- [ ] Generated unique `GO_SCRAPER_API_KEY`
- [ ] Adjusted `CELERY_CONCURRENCY` for your system
- [ ] Set appropriate `MAX_DETAIL_PAGES_PER_JOB`
- [ ] Configured delays (`DETAIL_PAGE_DELAY_MIN/MAX`)
- [ ] Set `ENV=production` (if production)
- [ ] Configured monitoring (Sentry)
- [ ] Configured email (SMTP)
- [ ] Set data retention policy
- [ ] Tested the configuration
- [ ] Verified `.env` is in `.gitignore`
- [ ] Never committed `.env` to Git

---

## 📞 Need Help?

- **Documentation:** Check `SETUP.md` for setup instructions
- **Security:** Check `SECURITY_VERIFICATION_COMPLETE.md`
- **Troubleshooting:** Check `SETUP.md` troubleshooting section
- **Logs:** `docker-compose logs -f`

---

**Last Updated:** May 27, 2026  
**Version:** 1.0
