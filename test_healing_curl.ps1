# Simple curl test for healing-stats endpoint

Write-Host "Getting admin token..." -ForegroundColor Yellow

# Login
$loginJson = '{"email":"admin@example.com","password":"admin123"}'
$loginResult = curl -s -X POST http://localhost:8000/api/v1/auth/login `
    -H "Content-Type: application/json" `
    -d $loginJson

$token = ($loginResult | ConvertFrom-Json).access_token

if ($token) {
    Write-Host "Token obtained: $($token.Substring(0,20))..." -ForegroundColor Green
    Write-Host ""
    Write-Host "Calling healing-stats endpoint..." -ForegroundColor Yellow
    Write-Host ""
    
    # Call healing-stats
    curl -s http://localhost:8000/api/v1/admin/healing-stats `
        -H "Authorization: Bearer $token" | ConvertFrom-Json | ConvertTo-Json -Depth 10
} else {
    Write-Host "Failed to get token" -ForegroundColor Red
    Write-Host "Login result: $loginResult" -ForegroundColor Gray
}
