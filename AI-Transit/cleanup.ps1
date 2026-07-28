# ============================================================
# cleanup.ps1 — Transit AI System Project Cleanup
# Run this once from the project root:
#   .\cleanup.ps1
# ============================================================

$root = "f:\transit-ai-system"

Write-Host "`n=== Step 1: Deleting empty Python files ===" -ForegroundColor Cyan

$emptyFiles = @(
    "$root\ml\drl\train_drl.py",
    "$root\ml\drl\dqn_agent.py",
    "$root\ml\drl\environment.py",
    "$root\ml\drl\replay.py",
    "$root\ml\milp\optimizer.py",
    "$root\ml\milp\constraints.py",
    "$root\ml\milp\fleet_allocator.py"
)

foreach ($f in $emptyFiles) {
    if (Test-Path $f) {
        $size = (Get-Item $f).Length
        if ($size -eq 0) {
            Remove-Item $f -Force
            Write-Host "  Deleted (empty): $f" -ForegroundColor Red
        } else {
            Write-Host "  Skipped (not empty, $size bytes): $f" -ForegroundColor Yellow
        }
    }
}

Write-Host "`n=== Step 2: Deleting trivial one-off test scripts in scripts/ ===" -ForegroundColor Cyan

$trivialScripts = @(
    "$root\scripts\test.py",
    "$root\scripts\test_env.py",
    "$root\scripts\tests.py"
)

foreach ($f in $trivialScripts) {
    if (Test-Path $f) {
        Remove-Item $f -Force
        Write-Host "  Deleted (trivial): $f" -ForegroundColor Red
    }
}

Write-Host "`n=== Step 3: Deleting empty directories ===" -ForegroundColor Cyan

$emptyDirs = @(
    "$root\ml\cgb"
)

foreach ($d in $emptyDirs) {
    if (Test-Path $d) {
        $items = Get-ChildItem $d -Force
        if ($items.Count -eq 0) {
            Remove-Item $d -Force -Recurse
            Write-Host "  Deleted (empty dir): $d" -ForegroundColor Red
        } else {
            Write-Host "  Skipped (not empty): $d" -ForegroundColor Yellow
        }
    }
}

Write-Host "`n=== Step 4: Removing root-level Python scripts (now moved to scripts/) ===" -ForegroundColor Cyan

$movedScripts = @(
    "$root\benchmark_dql.py",
    "$root\check_stops.py",
    "$root\inspect_model.py",
    "$root\inspect_routes.py",
    "$root\search.py",
    "$root\search_api.py",
    "$root\search_frontend.py",
    "$root\seed_predictions.py",
    "$root\test_backend.py",
    "$root\test_dql_endpoints.py",
    "$root\test_import.py",
    "$root\test_plan_trip.py"
)

foreach ($f in $movedScripts) {
    if (Test-Path $f) {
        $scriptName = [System.IO.Path]::GetFileName($f)
        $dest = "$root\scripts\$scriptName"
        if (Test-Path $dest) {
            Remove-Item $f -Force
            Write-Host "  Removed root copy (moved to scripts/): $scriptName" -ForegroundColor Green
        } else {
            Write-Host "  WARNING: scripts/$scriptName not found - keeping root copy!" -ForegroundColor Yellow
        }
    }
}

Write-Host "`n=== Cleanup Complete! ===" -ForegroundColor Green
Write-Host "Run 'Get-ChildItem -Recurse -File -Filter *.py | Where-Object { `$_.Length -eq 0 }' to verify no empty files remain."
