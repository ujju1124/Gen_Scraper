# Docker Desktop Startup Fix Script
# Run this when Docker Desktop is stuck starting

Write-Host "=== Docker Desktop Startup Fix ===" -ForegroundColor Cyan
Write-Host ""

# Step 1: Check current status
Write-Host "Step 1: Checking Docker status..." -ForegroundColor Yellow
$dockerProcesses = Get-Process -Name "Docker Desktop" -ErrorAction SilentlyContinue
if ($dockerProcesses) {
    Write-Host "  Found $($dockerProcesses.Count) Docker Desktop processes" -ForegroundColor Green
} else {
    Write-Host "  No Docker Desktop processes found" -ForegroundColor Red
}

$dockerService = Get-Service -Name "com.docker.service" -ErrorAction SilentlyContinue
if ($dockerService) {
    Write-Host "  Docker service status: $($dockerService.Status)" -ForegroundColor Green
} else {
    Write-Host "  Docker service not found" -ForegroundColor Red
}

# Step 2: Check memory
Write-Host ""
Write-Host "Step 2: Checking system memory..." -ForegroundColor Yellow
$os = Get-CimInstance Win32_OperatingSystem
$freeMemGB = [math]::Round($os.FreePhysicalMemory/1MB, 2)
$totalMemGB = [math]::Round($os.TotalVisibleMemorySize/1MB, 2)
Write-Host "  Free Memory: $freeMemGB GB / $totalMemGB GB" -ForegroundColor Green

if ($freeMemGB -lt 2) {
    Write-Host "  WARNING: Low memory! Docker may fail to start." -ForegroundColor Red
    Write-Host "  Recommendation: Close unnecessary applications" -ForegroundColor Yellow
}

# Step 3: Kill stuck Docker processes
Write-Host ""
Write-Host "Step 3: Stopping Docker Desktop..." -ForegroundColor Yellow
Write-Host "  Closing Docker Desktop application..." -ForegroundColor Gray

# Try graceful shutdown first
$dockerProcesses = Get-Process -Name "Docker Desktop" -ErrorAction SilentlyContinue
if ($dockerProcesses) {
    $dockerProcesses | ForEach-Object {
        try {
            $_.CloseMainWindow() | Out-Null
        } catch {
            Write-Host "  Could not close window for process $($_.Id)" -ForegroundColor Gray
        }
    }
    Start-Sleep -Seconds 5
}

# Force kill if still running
$dockerProcesses = Get-Process -Name "Docker Desktop" -ErrorAction SilentlyContinue
if ($dockerProcesses) {
    Write-Host "  Force stopping Docker Desktop processes..." -ForegroundColor Gray
    $dockerProcesses | Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
}

# Kill backend processes
Write-Host "  Stopping Docker backend processes..." -ForegroundColor Gray
Get-Process -Name "com.docker.backend" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Get-Process -Name "vpnkit" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Get-Process -Name "com.docker.proxy" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue

Start-Sleep -Seconds 3

# Step 4: Clean up Docker data (optional - commented out for safety)
# Write-Host ""
# Write-Host "Step 4: Cleaning Docker data..." -ForegroundColor Yellow
# $dockerDataPath = "$env:LOCALAPPDATA\Docker"
# if (Test-Path $dockerDataPath) {
#     Remove-Item "$dockerDataPath\*.lock" -Force -ErrorAction SilentlyContinue
#     Write-Host "  Removed lock files" -ForegroundColor Green
# }

# Step 5: Restart Docker Desktop
Write-Host ""
Write-Host "Step 4: Starting Docker Desktop..." -ForegroundColor Yellow

# Find Docker Desktop executable
$dockerPath = "C:\Program Files\Docker\Docker\Docker Desktop.exe"
if (-not (Test-Path $dockerPath)) {
    $dockerPath = "${env:ProgramFiles}\Docker\Docker\Docker Desktop.exe"
}

if (Test-Path $dockerPath) {
    Write-Host "  Launching Docker Desktop..." -ForegroundColor Gray
    Start-Process $dockerPath
    
    Write-Host ""
    Write-Host "Waiting for Docker to start (this may take 1-2 minutes)..." -ForegroundColor Cyan
    Write-Host "Checking every 10 seconds..." -ForegroundColor Gray
    
    $maxAttempts = 12  # 2 minutes
    $attempt = 0
    $dockerReady = $false
    
    while ($attempt -lt $maxAttempts -and -not $dockerReady) {
        Start-Sleep -Seconds 10
        $attempt++
        
        Write-Host "  Attempt $attempt/$maxAttempts..." -ForegroundColor Gray
        
        # Check if docker command works
        $result = docker ps 2>&1
        if ($LASTEXITCODE -eq 0) {
            $dockerReady = $true
            Write-Host ""
            Write-Host "SUCCESS! Docker is ready!" -ForegroundColor Green
            docker ps
        } else {
            Write-Host "    Still starting..." -ForegroundColor Gray
        }
    }
    
    if (-not $dockerReady) {
        Write-Host ""
        Write-Host "Docker is taking longer than expected to start." -ForegroundColor Yellow
        Write-Host ""
        Write-Host "Possible issues:" -ForegroundColor Yellow
        Write-Host "  1. Low memory (need at least 4GB free)" -ForegroundColor Gray
        Write-Host "  2. WSL2 not running (check: wsl --status)" -ForegroundColor Gray
        Write-Host "  3. Hyper-V disabled" -ForegroundColor Gray
        Write-Host "  4. Antivirus blocking Docker" -ForegroundColor Gray
        Write-Host ""
        Write-Host "Try these solutions:" -ForegroundColor Cyan
        Write-Host "  1. Close unnecessary applications to free memory" -ForegroundColor Gray
        Write-Host "  2. Restart your computer" -ForegroundColor Gray
        Write-Host "  3. Check Docker Desktop logs in system tray icon" -ForegroundColor Gray
    }
    
} else {
    Write-Host "  ERROR: Docker Desktop not found at: $dockerPath" -ForegroundColor Red
    Write-Host "  Please install Docker Desktop or update the path in this script" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=== Script Complete ===" -ForegroundColor Cyan
