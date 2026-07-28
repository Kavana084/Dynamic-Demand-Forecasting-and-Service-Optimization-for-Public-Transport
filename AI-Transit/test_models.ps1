Write-Host "========================================="
Write-Host "  Transit AI System - Model Diagnostics  "
Write-Host "========================================="
Write-Host ""

# 1. Test CatBoost (Demand Prediction)
Write-Host "[1/3] Testing CatBoost Model (Demand Prediction)..." -ForegroundColor Cyan
$catboostBody = @{
    route_id = "500C"
    hour = 8
    weather = "Clear"
    traffic = "Medium"
} | ConvertTo-Json

try {
    $catResponse = Invoke-RestMethod -Uri "http://localhost:8000/api/predict_demand" -Method Post -Headers @{"Content-Type"="application/json"} -Body $catboostBody
    Write-Host "✅ CatBoost Success!" -ForegroundColor Green
    Write-Host "   Predicted Demand: $($catResponse.predicted_demand) passengers"
    Write-Host "   Route: $($catResponse.route_id)"
} catch {
    Write-Host "❌ CatBoost Failed. Is the FastAPI server running on port 8000?" -ForegroundColor Red
    Write-Host $_.Exception.Message
}
Write-Host ""

# 2. Test MILP (Fleet Optimization)
Write-Host "[2/3] Testing MILP Engine (Fleet Optimization)..." -ForegroundColor Cyan
Write-Host "      (This takes a few seconds as it solves the allocation matrix)"
$milpBody = @{
    bus_capacity = 60
    max_buses_per_route = 15
    cost_per_bus = 200
    penalty_unmet_demand = 50
    alpha = 1.0
    beta = 0.5
    gamma = 2.0
    delta = 1.0
} | ConvertTo-Json

try {
    $milpResponse = Invoke-RestMethod -Uri "http://localhost:8000/api/optimize_fleet" -Method Post -Headers @{"Content-Type"="application/json"} -Body $milpBody -TimeoutSec 60
    Write-Host "✅ MILP Solver Success!" -ForegroundColor Green
    Write-Host "   Solver Status: $($milpResponse.status)"
    Write-Host "   Total Buses Used: $($milpResponse.summary.total_buses_used)"
    Write-Host "   Overall Efficiency: $($milpResponse.summary.overall_efficiency_percent)%"
} catch {
    Write-Host "❌ MILP Engine Failed. Check server logs." -ForegroundColor Red
    Write-Host $_.Exception.Message
}
Write-Host ""

# 3. Test DQL (Reinforcement Learning Placeholder)
Write-Host "[3/3] Testing DQL / Reinforcement Learning..." -ForegroundColor Cyan
try {
    $dqlResponse = Invoke-RestMethod -Uri "http://localhost:8000/api/dashboard" -Method Get
    Write-Host "✅ DQL Mock Accessed!" -ForegroundColor Green
    Write-Host "   Recommended Action: $($dqlResponse.drlRecommendation.action)"
    Write-Host "   Expected Reward: $($dqlResponse.drlRecommendation.expectedReward)"
    Write-Host "   (Note: This is currently returning placeholder JSON data, not an active python DRL model)"
} catch {
    Write-Host "❌ Dashboard API Failed." -ForegroundColor Red
    Write-Host $_.Exception.Message
}
Write-Host ""
Write-Host "Diagnostics Complete." -ForegroundColor Green
