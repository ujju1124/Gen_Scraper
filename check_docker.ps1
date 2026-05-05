# Quick Docker Status Checker

Write-Host "=== Docker Status Checker ===" -ForegroundColor Cyan
Write-Host ""

Write-Host "Checking Docker daemon..." -ForegroundColor Yellow

$maxAttempts = 10
$attempt = 0
$dockerReady = $false

while ($attempt -lt $maxAttempts) {
    $attempt++
    
    try {
        $result = docker ps 2>&1
        if ($LASTEXITCODE -eq 0) {
            $dockerReady = $true
            break
        }
    } catch {}
    
    Write-Host "Attempt $attempt/$maxAttempts - Docker not ready yet..." -ForegroundColor Gray
    Start-Sleep -Seconds 3
}

Write-Host ""

if ($dockerReady) {
    Write-Host "✓ Docker is ready!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Current status:" -ForegroundColor Yellow
    docker ps
    Write-Host ""
    Write-Host "Images:" -ForegroundColor Yellow
    docker images
    Write-Host ""
    Write-Host "You can now run: .\rebuild.ps1" -ForegroundColor Cyan
} else {
    Write-Host "✗ Docker is still starting up" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please wait and check:" -ForegroundColor Yellow
    Write-Host "1. Docker Desktop icon in system tray should be stable" -ForegroundColor White
    Write-Host "2. Right-click icon → should say 'Docker Desktop is running'" -ForegroundColor White
    Write-Host ""
    Write-Host "Then run this script again: .\check_docker.ps1" -ForegroundColor Cyan
}
