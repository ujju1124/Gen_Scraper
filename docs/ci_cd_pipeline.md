# CI/CD Pipeline Documentation

**Created**: April 29, 2026  
**Pipeline**: GitHub Actions  
**Status**: Active

---

## Overview

The Gen Scraper project uses GitHub Actions for continuous integration and continuous deployment. The pipeline automatically tests, builds, and deploys code changes.

---

## Pipeline Stages

### 1. Backend Tests (`backend-tests`)

**Triggers**: Every push to main/develop, all pull requests  
**Duration**: ~3-5 minutes  
**Services**: PostgreSQL 15, Redis 7

**Steps**:
1. Checkout code
2. Setup Python 3.11 with pip caching
3. Install dependencies from `backend/requirements.txt`
4. Run Alembic migrations on test database
5. Run pytest with coverage
6. Check coverage threshold (≥85%)
7. Upload coverage to Codecov

**Environment Variables**:
- `DATABASE_URL`: Test database connection
- `TEST_DATABASE_URL`: Same as DATABASE_URL
- `REDIS_URL`: Redis connection
- `SECRET_KEY`: Test secret key
- `MOCK_MODE`: "true" (disables external API calls)

**Coverage Threshold**: 85% (fails if below)

---

### 2. Frontend Tests (`frontend-tests`)

**Triggers**: Every push to main/develop, all pull requests  
**Duration**: ~2-4 minutes  
**Services**: None

**Steps**:
1. Checkout code
2. Setup Node.js 20 with npm caching
3. Install dependencies with `npm ci`
4. Run ESLint for code quality
5. Run Vitest with coverage
6. Check coverage threshold (≥75%)
7. Upload coverage to Codecov

**Coverage Threshold**: 75% (configured in vite.config.js)

---

### 3. Build Docker Images (`build-docker`)

**Triggers**: Push to main branch only (after tests pass)  
**Duration**: ~5-8 minutes  
**Dependencies**: backend-tests, frontend-tests

**Steps**:
1. Checkout code
2. Setup Docker Buildx
3. Login to Docker Hub
4. Build and push backend image with caching
5. Build and push frontend image with caching
6. Scan images for vulnerabilities (Trivy)
7. Upload security scan results

**Image Tags**:
- `main` - Latest main branch
- `main-<sha>` - Specific commit

**Caching**: Registry-based caching for faster builds

---

### 4. Deploy to Staging (`deploy-staging`)

**Triggers**: Push to main branch only (after Docker build)  
**Duration**: ~2-3 minutes  
**Dependencies**: build-docker  
**Environment**: staging

**Steps**:
1. Checkout code
2. Setup SSH with private key
3. Connect to staging server
4. Pull latest Docker images
5. Run database migrations
6. Restart services with `docker-compose up -d`
7. Wait 30 seconds for startup
8. Run health checks
9. Send Slack notification (success/failure)

**Health Checks**:
- `https://staging.example.com/health`
- `https://staging.example.com/api/v1/health`

**Rollback**: Manual (if health checks fail, previous version remains)

---

### 5. Deploy to Production (`deploy-production`)

**Triggers**: Push to main branch only (after staging deployment)  
**Duration**: ~3-5 minutes  
**Dependencies**: deploy-staging  
**Environment**: production (requires manual approval)

**Steps**:
1. Checkout code
2. Setup SSH with private key
3. **Backup production database**
4. Connect to production server
5. Pull latest Docker images
6. Run database migrations
7. Blue-green deployment (start new containers)
8. Health check new containers
9. Switch traffic to new containers
10. Run final health checks
11. Send Slack + Email notifications

**Health Checks**:
- `https://app.example.com/health`
- `https://app.example.com/api/v1/health`

**Rollback**: Automatic on health check failure

**Manual Approval**: Required before production deployment

---

## Required GitHub Secrets

### Docker Hub
- `DOCKER_USERNAME` - Docker Hub username
- `DOCKER_PASSWORD` - Docker Hub password or access token

### SSH Access
- `SSH_PRIVATE_KEY` - Private SSH key for server access

### Staging Environment
- `STAGING_HOST` - Staging server hostname/IP
- `STAGING_USER` - SSH username for staging

### Production Environment
- `PRODUCTION_HOST` - Production server hostname/IP
- `PRODUCTION_USER` - SSH username for production

### Notifications
- `SLACK_WEBHOOK` - Slack webhook URL for notifications
- `EMAIL_USERNAME` - SMTP username (Gmail)
- `EMAIL_PASSWORD` - SMTP password (Gmail app password)
- `NOTIFICATION_EMAIL` - Email address for notifications

---

## Setting Up GitHub Secrets

1. Go to repository Settings → Secrets and variables → Actions
2. Click "New repository secret"
3. Add each secret from the list above
4. For SSH key: `cat ~/.ssh/id_rsa | pbcopy` (copy private key)
5. For Slack webhook: Create incoming webhook in Slack workspace

---

## Environment Protection Rules

### Staging
- No approval required
- Auto-deploys on main branch push

### Production
- **Manual approval required**
- Requires review from repository admin
- Timeout: 30 days

To configure:
1. Go to Settings → Environments
2. Click "production"
3. Enable "Required reviewers"
4. Add reviewers

---

## Workflow Diagram

```
Push to main/develop
        │
        ├─────────────┬─────────────┐
        ▼             ▼             ▼
  Backend Tests  Frontend Tests  (Parallel)
        │             │
        └──────┬──────┘
               ▼
        All Tests Pass?
               │
               ▼ (main only)
        Build Docker Images
               │
               ▼
        Scan for Vulnerabilities
               │
               ▼
        Deploy to Staging
               │
               ▼
        Health Checks Pass?
               │
               ▼
        Manual Approval
               │
               ▼
        Deploy to Production
               │
               ▼
        Health Checks Pass?
               │
        ├─────────┬─────────┐
        ▼         ▼         ▼
    Success   Failure   Rollback
```

---

## Testing the Pipeline

### Test on Pull Request
```bash
git checkout -b test-ci
git commit --allow-empty -m "Test CI pipeline"
git push origin test-ci
# Create PR on GitHub
# Watch Actions tab for results
```

### Test Full Pipeline (Main Branch)
```bash
git checkout main
git commit --allow-empty -m "Test full CI/CD pipeline"
git push origin main
# Watch Actions tab
# Approve production deployment when prompted
```

---

## Monitoring

### GitHub Actions
- View all runs: Repository → Actions tab
- View specific run: Click on workflow run
- Download logs: Click "..." → Download logs
- Re-run failed jobs: Click "Re-run jobs"

### Codecov
- View coverage: https://codecov.io/gh/YOUR_ORG/gen-scraper
- Coverage trends over time
- File-level coverage details

### Slack Notifications
- Deployment success/failure
- Includes commit SHA, branch, author
- Links to GitHub Actions logs

---

## Troubleshooting

### Tests Failing
1. Check test logs in Actions tab
2. Run tests locally: `docker-compose run --rm backend pytest tests/ -v`
3. Check for environment-specific issues

### Docker Build Failing
1. Check Dockerfile syntax
2. Verify all dependencies are in requirements.txt/package.json
3. Test build locally: `docker build -t test ./backend`

### Deployment Failing
1. Check SSH connection: `ssh user@host`
2. Verify secrets are set correctly
3. Check server disk space: `df -h`
4. Check Docker on server: `docker ps`

### Health Checks Failing
1. Check application logs: `docker-compose logs backend`
2. Verify health endpoints: `curl http://localhost:8000/health`
3. Check database connection
4. Check Redis connection

---

## Coverage Badges

Add to README.md:

```markdown
[![Backend Coverage](https://codecov.io/gh/YOUR_ORG/gen-scraper/branch/main/graph/badge.svg?flag=backend)](https://codecov.io/gh/YOUR_ORG/gen-scraper)
[![Frontend Coverage](https://codecov.io/gh/YOUR_ORG/gen-scraper/branch/main/graph/badge.svg?flag=frontend)](https://codecov.io/gh/YOUR_ORG/gen-scraper)
[![CI/CD](https://github.com/YOUR_ORG/gen-scraper/actions/workflows/ci.yml/badge.svg)](https://github.com/YOUR_ORG/gen-scraper/actions/workflows/ci.yml)
```

---

## Best Practices

### Commits
- Write clear commit messages
- Reference issue numbers: `Fix #123: Update scraper`
- Keep commits focused and atomic

### Pull Requests
- Wait for CI to pass before merging
- Review coverage reports
- Address linting issues

### Deployments
- Always test in staging first
- Monitor logs after deployment
- Keep database backups
- Have rollback plan ready

### Secrets
- Rotate secrets regularly (every 90 days)
- Use least privilege access
- Never commit secrets to repository
- Use environment-specific secrets

---

## Maintenance

### Weekly
- Review failed builds
- Check coverage trends
- Update dependencies (Dependabot)

### Monthly
- Rotate SSH keys
- Review and update secrets
- Check disk space on servers
- Review security scan results

### Quarterly
- Update GitHub Actions versions
- Review and optimize pipeline
- Update documentation
- Audit access permissions

---

## Future Improvements

- [ ] Add performance testing stage
- [ ] Implement canary deployments
- [ ] Add smoke tests after deployment
- [ ] Integrate with monitoring (Datadog, New Relic)
- [ ] Add automatic dependency updates
- [ ] Implement feature flags
- [ ] Add database migration rollback
- [ ] Implement multi-region deployment

---

**Last Updated**: April 29, 2026  
**Maintained By**: DevOps Team  
**Contact**: devops@example.com
