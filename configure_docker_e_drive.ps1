# Configure Docker Desktop to use E: Drive

Write-Host "=== Configure Docker to Use E: Drive ===" -ForegroundColor Cyan
Write-Host ""

Write-Host "Docker Desktop is starting..." -ForegroundColor Yellow
Write-Host ""
Write-Host "MANUAL STEPS REQUIRED:" -ForegroundColor Red
Write-Host ""
Write-Host "1. Wait for Docker Desktop to fully start (whale icon stable in system tray)" -ForegroundColor White
Write-Host ""
Write-Host "2. Click the gear icon (⚙️) in Docker Desktop" -ForegroundColor White
Write-Host ""
Write-Host "3. Go to: Resources → Advanced" -ForegroundColor White
Write-Host ""
Write-Host "4. Look for 'Disk image location' or similar setting" -ForegroundColor White
Write-Host ""
Write-Host "5. Change it to: E:\Docker" -ForegroundColor Yellow
Write-Host ""
Write-Host "6. Click 'Apply & Restart'" -ForegroundColor White
Write-Host ""
Write-Host "7. Wait for Docker to restart (2-3 minutes)" -ForegroundColor White
Write-Host ""
Write-Host "8. Come back here and press Enter" -ForegroundColor White
Write-Host ""

Read-Host "Press Enter after you've configured Docker to use E:\Docker"

Write-Host ""
Write-Host "Verifying Docker is ready..." -ForegroundColor Yellow

$maxAttempts = 20
$attempt = 0

while ($attempt -lt $maxAttempts) {
    $attempt++
    try {
        docker version | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✓ Docker is ready!" -ForegroundColor Green
            break
        }
    } catch {}
    Write-Host "Waiting... ($attempt/$maxAttempts)" -ForegroundColor Gray
    Start-Sleep -Seconds 3
}

if ($attempt -eq $maxAttempts) {
    Write-Host "✗ Docker did not start" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Testing Docker..." -ForegroundColor Yellow
docker ps

Write-Host ""
Write-Host "✓ Docker is configured and ready!" -ForegroundColor Green
Write-Host ""
Write-Host "Next step: Run .\rebuild.ps1" -ForegroundColor Cyan
