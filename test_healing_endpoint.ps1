# Test Healing Stats Endpoint
# This script logs in as admin and tests the healing-stats endpoint

Write-Host "=== Testing Healing Stats Endpoint ===" -ForegroundColor Cyan
Write-Host ""

# Step 1: Login as admin
Write-Host "Step 1: Logging in as admin..." -ForegroundColor Yellow
$loginBody = @{
    email = "admin@example.com"
    password = "admin123"
} | ConvertTo-Json

try {
    $loginResponse = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/auth/login" `
        -Method POST `
        -Body $loginBody `
        -ContentType "application/json"
    
    $token = $loginResponse.access_token
    Write-Host "  Login successful! Token obtained." -ForegroundColor Green
} catch {
    Write-Host "  Login failed: $_" -ForegroundColor Red
    exit 1
}

# Step 2: Call healing-stats endpoint
Write-Host ""
Write-Host "Step 2: Fetching healing stats..." -ForegroundColor Yellow

try {
    $headers = @{
        "Authorization" = "Bearer $token"
    }
    
    $healingStats = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/admin/healing-stats" `
        -Method GET `
        -Headers $headers
    
    Write-Host "  Success! Healing stats retrieved." -ForegroundColor Green
    Write-Host ""
    
    # Display stats
    Write-Host "=== Healing System Statistics ===" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Total Attempts:  $($healingStats.total_attempts)" -ForegroundColor White
    Write-Host "Resolved:        $($healingStats.resolved)" -ForegroundColor Green
    Write-Host "Pending:         $($healingStats.pending)" -ForegroundColor Yellow
    Write-Host "Success Rate:    $($healingStats.success_rate)%" -ForegroundColor White
    Write-Host "Avg Confidence:  $($healingStats.avg_confidence)" -ForegroundColor White
    Write-Host ""
    
    # Display recent heals
    Write-Host "=== Recent Heals (Top 5) ===" -ForegroundColor Cyan
    Write-Host ""
    
    $recentHeals = $healingStats.recent_heals | Select-Object -First 5
    
    foreach ($heal in $recentHeals) {
        $statusColor = if ($heal.status -eq "RESOLVED") { "Green" } else { "Yellow" }
        $confColor = if ($heal.confidence -ge 0.7) { "Green" } else { "DarkYellow" }
        
        Write-Host "Source: $($heal.source_name)" -ForegroundColor White
        Write-Host "  Field: $($heal.field_name)" -ForegroundColor Gray
        Write-Host "  Old: $($heal.old_selector)" -ForegroundColor Gray
        Write-Host "  New: $($heal.new_selector)" -ForegroundColor Gray
        Write-Host "  Confidence: $($heal.confidence)" -ForegroundColor $confColor
        Write-Host "  Status: $($heal.status)" -ForegroundColor $statusColor
        Write-Host "  Time: $($heal.created_at)" -ForegroundColor Gray
        Write-Host ""
    }
    
    # Output full JSON for verification
    Write-Host "=== Full JSON Response ===" -ForegroundColor Cyan
    $healingStats | ConvertTo-Json -Depth 10
    
} catch {
    Write-Host "  Failed to fetch healing stats: $_" -ForegroundColor Red
    Write-Host "  Error details: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "=== Test Complete ===" -ForegroundColor Green
