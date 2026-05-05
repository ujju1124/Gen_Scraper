# Docker Recovery Script
# Run this after Docker Desktop is fully started

Write-Host "=== Docker Recovery Script ===" -ForegroundColor Cyan
Write-Host ""

# Step 1: Check Docker is running
Write-Host "Step 1: Checking Docker status..." -ForegroundColor Yellow
try {
    docker version | Out-Null
    Write-Host "✓ Docker is running" -ForegroundColor Green
} catch {
    Write-Host "✗ Docker is not running. Please start Docker Desktop first." -ForegroundColor Red
    exit 1
}

Write-Host ""

# Step 2: Clean up any partial builds
Write-Host "Step 2: Cleaning up..." -ForegroundColor Yellow
docker-compose down -v 2>$null
Write-Host "✓ Cleaned up old containers" -ForegroundColor Green

Write-Host ""

# Step 3: Build and start containers
Write-Host "Step 3: Building containers (this takes 5-10 minutes)..." -ForegroundColor Yellow
Write-Host "Building backend..." -ForegroundColor Gray
docker-compose build backend

Write-Host "Building frontend..." -ForegroundColor Gray
docker-compose build frontend

Write-Host "✓ Images built" -ForegroundColor Green

Write-Host ""

# Step 4: Start all services
Write-Host "Step 4: Starting all services..." -ForegroundColor Yellow
docker-compose up -d

Write-Host "Waiting for containers to start..." -ForegroundColor Gray
Start-Sleep -Seconds 10

Write-Host "✓ Containers started" -ForegroundColor Green

Write-Host ""

# Step 5: Check container status
Write-Host "Step 5: Checking container status..." -ForegroundColor Yellow
docker-compose ps

Write-Host ""

# Step 6: Wait for postgres to be ready
Write-Host "Step 6: Waiting for PostgreSQL to be ready..." -ForegroundColor Yellow
$maxAttempts = 30
$attempt = 0

while ($attempt -lt $maxAttempts) {
    $attempt++
    try {
        docker exec gen_scraper-postgres-1 pg_isready -U scraper 2>$null | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✓ PostgreSQL is ready" -ForegroundColor Green
            break
        }
    } catch {}
    
    Write-Host "Waiting... ($attempt/$maxAttempts)" -ForegroundColor Gray
    Start-Sleep -Seconds 2
}

if ($attempt -eq $maxAttempts) {
    Write-Host "✗ PostgreSQL did not start in time" -ForegroundColor Red
    Write-Host "Check logs: docker logs gen_scraper-postgres-1" -ForegroundColor Yellow
    exit 1
}

Write-Host ""

# Step 7: Run migrations
Write-Host "Step 7: Running database migrations..." -ForegroundColor Yellow
docker exec gen_scraper-backend-1 alembic upgrade head

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Migrations complete" -ForegroundColor Green
} else {
    Write-Host "✗ Migrations failed" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Step 8: Seed database
Write-Host "Step 8: Seeding database..." -ForegroundColor Yellow
docker exec gen_scraper-backend-1 python seed.py

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Database seeded" -ForegroundColor Green
} else {
    Write-Host "✗ Seeding failed" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Step 9: Verify
Write-Host "Step 9: Verifying setup..." -ForegroundColor Yellow

Write-Host "Checking categories..." -ForegroundColor Gray
$categories = docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -t -c "SELECT COUNT(*) FROM categories;"
Write-Host "  Categories: $($categories.Trim())" -ForegroundColor White

Write-Host "Checking sources..." -ForegroundColor Gray
$sources = docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -t -c "SELECT COUNT(*) FROM sources WHERE is_active=true;"
Write-Host "  Active sources: $($sources.Trim())" -ForegroundColor White

Write-Host "Checking admin user..." -ForegroundColor Gray
$admin = docker exec gen_scraper-postgres-1 psql -U scraper -d scraper_db -t -c "SELECT email FROM users WHERE role='admin' LIMIT 1;"
Write-Host "  Admin email: $($admin.Trim())" -ForegroundColor White

Write-Host ""
Write-Host "✓ Setup complete!" -ForegroundColor Green

Write-Host ""
Write-Host "=== Next Steps ===" -ForegroundColor Cyan
Write-Host "1. Open browser: http://localhost:5173" -ForegroundColor White
Write-Host "2. Login with: admin@example.com / admin123" -ForegroundColor White
Write-Host "3. Start Batch 1: python bulk_job_creator.py --batch 1" -ForegroundColor White
Write-Host "4. Monitor: python monitor_batch1.py" -ForegroundColor White
Write-Host ""
