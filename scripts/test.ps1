<#
.SYNOPSIS
  Runs the backend tests, frontend tests and the frontend production build.
  Exits with a non-zero code if any step fails.
#>
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$failed = @()

Write-Host "`n==> Backend tests (pytest)" -ForegroundColor Cyan
Push-Location (Join-Path $Root "backend")
& ".venv\Scripts\python.exe" -m pytest
if ($LASTEXITCODE -ne 0) { $failed += "backend tests" }
Pop-Location

Push-Location (Join-Path $Root "frontend")
Write-Host "`n==> Frontend tests (vitest)" -ForegroundColor Cyan
& npm.cmd test
if ($LASTEXITCODE -ne 0) { $failed += "frontend tests" }
Write-Host "`n==> Frontend production build" -ForegroundColor Cyan
& npm.cmd run build
if ($LASTEXITCODE -ne 0) { $failed += "frontend build" }
Pop-Location

if ($failed.Count -gt 0) {
    Write-Host "`nFAILED: $($failed -join ', ')" -ForegroundColor Red
    exit 1
}
Write-Host "`nAll checks passed." -ForegroundColor Green
