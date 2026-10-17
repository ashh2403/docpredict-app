<#
.SYNOPSIS
  Starts the DocPredict web app on http://localhost:5173 (Ctrl+C to stop).
  Requests to /api are proxied to the backend on http://127.0.0.1:8000.
#>
$ErrorActionPreference = "Stop"
$Frontend = Join-Path (Split-Path -Parent $PSScriptRoot) "frontend"
if (-not (Test-Path (Join-Path $Frontend "node_modules"))) { throw "frontend\node_modules not found. Run scripts\setup.ps1 first." }

Set-Location $Frontend
Write-Host "DocPredict web app -> http://localhost:5173" -ForegroundColor Cyan
& npm.cmd run dev
