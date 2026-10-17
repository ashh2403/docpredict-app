<#
.SYNOPSIS
  Starts the DocPredict API on http://127.0.0.1:8000 (Ctrl+C to stop).
#>
param([int]$Port = 8000)

$ErrorActionPreference = "Stop"
$Backend = Join-Path (Split-Path -Parent $PSScriptRoot) "backend"
$VenvPython = Join-Path $Backend ".venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) { throw "backend\.venv not found. Run scripts\setup.ps1 first." }

Set-Location $Backend
Write-Host "DocPredict API -> http://127.0.0.1:$Port  (docs: http://127.0.0.1:$Port/docs)" -ForegroundColor Cyan
& $VenvPython -m uvicorn app.main:app --host 127.0.0.1 --port $Port
