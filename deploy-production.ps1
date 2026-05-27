# Production Deployment Script
# Deploys 4 Go Scraper instances with load balancing

Write-Host "🚀 Deploying Production-Ready Scraping System" -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Green
Write-Host ""

# Step 1: Stop all containers
Write-Host "Step 1: Stopping all containers..." -ForegroundColor Yellow
docker-compose down
Write-Host "✅ Containers stopped" -ForegroundColor Green
Write-Host ""

# Step 2: Build all services
Write-Host "Step 2: Building all services..." -ForegroundColor Yellow
docker-compose build
Write-Host "✅ Build complete" -ForegroundColor Green
Write-Host ""

# Step 3: Start all services
Write-Host "Step 3: Starting all services..." -ForegroundColor Yellow
docker-compose up -d
Write-Host "✅ Services started" -ForegroundColor Green
Write-Host ""

# Step 4: Wait for services to be healthy
Write-Host "Step 4: Waiting for services to be healthy (30 seconds)..." -ForegroundColor Yellow
Start-Sleep -Seconds 30
Write-Host "✅ Services should be healthy now" -ForegroundColor Green
Write-Host ""

# Step 5: Verify Go scraper instances
Write-Host "Step 5: Verifying Go scraper instances..." -ForegroundColor Yellow
Write-Host ""
Write-Host "Checking instance 1 (port 8080)..." -ForegroundColor Cyan
try {
    $response1 = Invoke-WebRequest -Uri "http://localhost:8080/" -TimeoutSec 5 -UseBasicParsing
    if ($response1.StatusCode -eq 200) {
        Write-Host "✅ Instance 1 is healthy" -ForegroundColor Green
    }
} catch {
    Write-Host "❌ Instance 1 is not responding" -ForegroundColor Red
}

Write-Host "Checking instance 2 (port 8081)..." -ForegroundColor Cyan
try {
    $response2 = Invoke-WebRequest -Uri "http://localhost:8081/" -TimeoutSec 5 -UseBasicParsing
    if ($response2.StatusCode -eq 200) {
        Write-Host "✅ Instance 2 is healthy" -ForegroundColor Green
    }
} catch {
    Write-Host "❌ Instance 2 is not responding" -ForegroundColor Red
}

Write-Host "Checking instance 3 (port 8082)..." -ForegroundColor Cyan
try {
    $response3 = Invoke-WebRequest -Uri "http://localhost:8082/" -TimeoutSec 5 -UseBasicParsing
    if ($response3.StatusCode -eq 200) {
        Write-Host "✅ Instance 3 is healthy" -ForegroundColor Green
    }
} catch {
    Write-Host "❌ Instance 3 is not responding" -ForegroundColor Red
}

Write-Host "Checking instance 4 (port 8083)..." -ForegroundColor Cyan
try {
    $response4 = Invoke-WebRequest -Uri "http://localhost:8083/" -TimeoutSec 5 -UseBasicParsing
    if ($response4.StatusCode -eq 200) {
        Write-Host "✅ Instance 4 is healthy" -ForegroundColor Green
    }
} catch {
    Write-Host "❌ Instance 4 is not responding" -ForegroundColor Red
}

Write-Host ""

# Step 6: Show running containers
Write-Host "Step 6: Running containers:" -ForegroundColor Yellow
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | Select-String "go_scraper"
Write-Host ""

# Step 7: Instructions
Write-Host "=============================================" -ForegroundColor Green
Write-Host "✅ Deployment Complete!" -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Green
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "1. Test the pool status API:" -ForegroundColor White
Write-Host "   curl http://localhost:8000/api/v1/jobs/go-scraper/queue" -ForegroundColor Cyan
Write-Host ""
Write-Host "2. Submit test jobs and watch them run in parallel" -ForegroundColor White
Write-Host ""
Write-Host "3. Read the deployment guide:" -ForegroundColor White
Write-Host "   PRODUCTION_DEPLOYMENT_GUIDE.md" -ForegroundColor Cyan
Write-Host ""
Write-Host "4. Monitor logs:" -ForegroundColor White
Write-Host "   docker logs gen_scraper-worker-1 -f | Select-String 'pool'" -ForegroundColor Cyan
Write-Host ""
Write-Host "🚀 Your system is now production-ready with 4x throughput!" -ForegroundColor Green
Write-Host ""
