<#
.SYNOPSIS
  Opens the backend and the frontend in two new PowerShell windows.
  Close those windows (or press Ctrl+C in them) to stop the app.
#>
$ErrorActionPreference = "Stop"
$Scripts = $PSScriptRoot

Start-Process powershell -ArgumentList @("-NoExit", "-ExecutionPolicy", "Bypass", "-File", (Join-Path $Scripts "start-backend.ps1"))
Start-Process powershell -ArgumentList @("-NoExit", "-ExecutionPolicy", "Bypass", "-File", (Join-Path $Scripts "start-frontend.ps1"))

Write-Host "Backend:  http://127.0.0.1:8000/api/health"
Write-Host "Web app:  http://localhost:5173  (may take a few seconds to start)"
