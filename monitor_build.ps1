# Monitor Docker Build Progress

Write-Host "=== Docker Build Monitor ===" -ForegroundColor Cyan
Write-Host ""

# Check if PID 10632 is still running
$buildProcess = Get-Process -Id 10632 -ErrorAction SilentlyContinue

if ($buildProcess) {
    Write-Host "✓ Build process (PID 10632) is running" -ForegroundColor Green
    Write-Host "  Started: $($buildProcess.StartTime)" -ForegroundColor Gray
    Write-Host "  CPU Time: $($buildProcess.CPU) seconds" -ForegroundColor Gray
    Write-Host ""
} else {
    Write-Host "✗ Build process (PID 10632) is not running" -ForegroundColor Red
    Write-Host ""
}

# Try to check Docker status
Write-Host "Checking Docker status..." -ForegroundColor Yellow

$dockerReady = $false
try {
    docker version | Out-Null
    if ($LASTEXITCODE -eq 0) {
        $dockerReady = $true
    }
} catch {}

if ($dockerReady) {
    Write-Host "✓ Docker daemon is ready" -ForegroundColor Green
    Write-Host ""
    
    # Show images
    Write-Host "=== Docker Images ===" -ForegroundColor Cyan
    docker images
    Write-Host ""
    
    # Show containers
    Write-Host "=== Docker Containers ===" -ForegroundColor Cyan
    docker ps -a
    Write-Host ""
    
    # Show build cache
    Write-Host "=== Build Cache ===" -ForegroundColor Cyan
    docker system df
    Write-Host ""
    
} else {
    Write-Host "⏳ Docker daemon is still initializing..." -ForegroundColor Yellow
    Write-Host "   This is normal during the first build after reinstall" -ForegroundColor Gray
    Write-Host ""
}

# Show what's next
Write-Host "=== What's Happening ===" -ForegroundColor Cyan
Write-Host "The build process is:" -ForegroundColor White
Write-Host "1. Waiting for Docker daemon to fully start" -ForegroundColor Gray
Write-Host "2. Building backend image (Python dependencies)" -ForegroundColor Gray
Write-Host "3. Building frontend image (Node.js dependencies)" -ForegroundColor Gray
Write-Host "4. Starting all containers" -ForegroundColor Gray
Write-Host "5. Running migrations and seeding database" -ForegroundColor Gray
Write-Host ""
Write-Host "This typically takes 15-20 minutes on first build" -ForegroundColor Yellow
Write-Host ""
Write-Host "Run this script again to check progress: .\monitor_build.ps1" -ForegroundColor Cyan
