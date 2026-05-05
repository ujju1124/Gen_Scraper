# Wait for Docker to be Ready

Write-Host "=== Waiting for Docker ===" -ForegroundColor Cyan
Write-Host ""

$maxWait = 300  # 5 minutes
$elapsed = 0
$checkInterval = 5

Write-Host "Checking Docker daemon every $checkInterval seconds..." -ForegroundColor Yellow
Write-Host "Press Ctrl+C to stop" -ForegroundColor Gray
Write-Host ""

while ($elapsed -lt $maxWait) {
    $timestamp = Get-Date -Format "HH:mm:ss"
    
    try {
        $null = docker ps 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "[$timestamp] ✓ Docker is ready!" -ForegroundColor Green
            Write-Host ""
            
            # Show current state
            Write-Host "Images built:" -ForegroundColor Cyan
            docker images --format "{{.Repository}}:{{.Tag}} ({{.Size}})"
            Write-Host ""
            
            Write-Host "Containers:" -ForegroundColor Cyan
            docker ps -a --format "{{.Names}} - {{.Status}}"
            Write-Host ""
            
            Write-Host "✓ Docker is operational!" -ForegroundColor Green
            Write-Host "The build process (PID 10632) can now proceed" -ForegroundColor White
            exit 0
        }
    } catch {}
    
    Write-Host "[$timestamp] ⏳ Docker daemon still initializing... ($elapsed/$maxWait seconds)" -ForegroundColor Yellow
    Start-Sleep -Seconds $checkInterval
    $elapsed += $checkInterval
}

Write-Host ""
Write-Host "✗ Docker did not start within $maxWait seconds" -ForegroundColor Red
Write-Host "Check Docker Desktop manually" -ForegroundColor Yellow
exit 1
