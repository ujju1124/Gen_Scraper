# Test healing-stats endpoint with cookie-based auth

$cookieFile = "cookies.txt"

Write-Host "Step 1: Login and save cookies..." -ForegroundColor Yellow
curl.exe -s -c $cookieFile -X POST http://localhost:8000/api/v1/auth/login `
    -H "Content-Type: application/json" `
    -d '{\"email\":\"admin@example.com\",\"password\":\"admin123\"}' | Out-Null

if (Test-Path $cookieFile) {
    Write-Host "  Cookies saved successfully" -ForegroundColor Green
} else {
    Write-Host "  Failed to save cookies" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Step 2: Call healing-stats with cookies..." -ForegroundColor Yellow
$response = curl.exe -s -b $cookieFile http://localhost:8000/api/v1/admin/healing-stats

Write-Host ""
Write-Host "=== Healing Stats Response ===" -ForegroundColor Cyan
Write-Host ""

try {
    $data = $response | ConvertFrom-Json
    
    # Display summary
    Write-Host "Total Attempts:  $($data.total_attempts)" -ForegroundColor White
    Write-Host "Resolved:        $($data.resolved)" -ForegroundColor Green
    Write-Host "Pending:         $($data.pending)" -ForegroundColor Yellow
    Write-Host "Success Rate:    $($data.success_rate)%" -ForegroundColor White
    Write-Host "Avg Confidence:  $($data.avg_confidence)" -ForegroundColor White
    Write-Host ""
    
    if ($data.recent_heals.Count -gt 0) {
        Write-Host "Recent Heals (Top 5):" -ForegroundColor Cyan
        $data.recent_heals | Select-Object -First 5 | ForEach-Object {
            Write-Host "  - $($_.source_name) / $($_.field_name): $($_.status) (conf: $($_.confidence))" -ForegroundColor Gray
        }
    } else {
        Write-Host "No healing attempts recorded yet." -ForegroundColor Gray
    }
    
    Write-Host ""
    Write-Host "=== Full JSON ===" -ForegroundColor Cyan
    $data | ConvertTo-Json -Depth 10
    
} catch {
    Write-Host "Error parsing response:" -ForegroundColor Red
    Write-Host $response -ForegroundColor Gray
}

# Cleanup
Remove-Item $cookieFile -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "=== Test Complete ===" -ForegroundColor Green
