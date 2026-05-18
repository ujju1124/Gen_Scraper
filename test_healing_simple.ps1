# Simple test using curl.exe directly

Write-Host "Step 1: Login..." -ForegroundColor Yellow
$loginResponse = curl.exe -s -X POST http://localhost:8000/api/v1/auth/login `
    -H "Content-Type: application/json" `
    -d '{\"email\":\"admin@example.com\",\"password\":\"admin123\"}'

Write-Host "Login response: $loginResponse" -ForegroundColor Gray
Write-Host ""

$tokenObj = $loginResponse | ConvertFrom-Json
$token = $tokenObj.access_token

if ($token) {
    Write-Host "Token: $($token.Substring(0,30))..." -ForegroundColor Green
    Write-Host ""
    Write-Host "Step 2: Call healing-stats..." -ForegroundColor Yellow
    
    $healingResponse = curl.exe -s http://localhost:8000/api/v1/admin/healing-stats `
        -H "Authorization: Bearer $token"
    
    Write-Host ""
    Write-Host "=== Healing Stats Response ===" -ForegroundColor Cyan
    $healingResponse | ConvertFrom-Json | ConvertTo-Json -Depth 10
} else {
    Write-Host "No token received" -ForegroundColor Red
}
