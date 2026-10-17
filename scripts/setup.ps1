<#
.SYNOPSIS
  One-time setup for DocPredict on Windows (safe to re-run).

.DESCRIPTION
  1. Creates backend\.venv and installs Python dependencies.
  2. Creates backend\.env with a freshly generated secret key (only if missing).
  3. Trains the classifier if ml\artifacts\model.joblib is missing (or -Retrain is given).
  4. Installs frontend dependencies.
  5. Writes sample documents to .\samples for manual testing.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
  powershell -ExecutionPolicy Bypass -File scripts\setup.ps1 -Retrain
#>
param([switch]$Retrain)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Backend = Join-Path $Root "backend"
$Frontend = Join-Path $Root "frontend"
$VenvPython = Join-Path $Backend ".venv\Scripts\python.exe"

function Step($msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Invoke-Checked {
    param([string]$Exe, [string[]]$Arguments)
    & $Exe @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Command failed ($LASTEXITCODE): $Exe $($Arguments -join ' ')" }
}

# Windows PowerShell 5.1 turns redirected stderr from a native program into a terminating error
# when $ErrorActionPreference is "Stop", so probes run with "Continue".
function Test-Native {
    param([string]$Exe, [string[]]$Arguments)
    $previous = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        & $Exe @Arguments 2>$null | Out-Null
        return ($LASTEXITCODE -eq 0)
    } catch {
        return $false
    } finally {
        $ErrorActionPreference = $previous
    }
}

Step "Checking prerequisites"
$pyExe = $null
$pyArgs = @()
$versionCheck = "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)"
if (Get-Command py -ErrorAction SilentlyContinue) {
    foreach ($v in @("3.12", "3.11", "3.10")) {
        if (Test-Native "py" @("-$v", "-c", $versionCheck)) { $pyExe = "py"; $pyArgs = @("-$v"); break }
    }
}
if (-not $pyExe -and (Get-Command python -ErrorAction SilentlyContinue)) {
    if (Test-Native "python" @("-c", $versionCheck)) { $pyExe = "python" }
}
if (-not $pyExe) { throw "Python 3.10 or newer is required (tested with 3.11). Install it from https://www.python.org/downloads/." }
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) { throw "Node.js 18+ (with npm) is required. Install it from https://nodejs.org/." }
Write-Host "Python: $(& $pyExe @pyArgs --version)   Node: $(node --version)"

Step "Creating Python virtual environment"
$VenvDir = Join-Path $Backend ".venv"
if ((Test-Path $VenvPython) -and -not (Test-Native $VenvPython @("-m", "pip", "--version"))) {
    Write-Host "backend\.venv is incomplete (no pip); recreating it"
    Remove-Item -Recurse -Force $VenvDir
}
if (-not (Test-Path $VenvPython)) {
    try {
        Invoke-Checked $pyExe ($pyArgs + @("-m", "venv", $VenvDir))
    } catch {
        if (Test-Path $VenvDir) { Remove-Item -Recurse -Force $VenvDir }
        throw ("Could not create the Python virtual environment. If the project folder path is very long " +
               "(Windows limits paths to 260 characters), move the project to a shorter path such as C:\docpredict " +
               "or enable Windows long path support, then re-run setup. Details: $_")
    }
} else { Write-Host "backend\.venv already exists" }

Step "Installing backend dependencies"
Invoke-Checked $VenvPython @("-m", "pip", "install", "--disable-pip-version-check", "-q", "-r", (Join-Path $Backend "requirements-dev.txt"))

Step "Creating backend\.env"
$EnvFile = Join-Path $Backend ".env"
if (-not (Test-Path $EnvFile)) {
    $secret = & $VenvPython -c "import secrets; print(secrets.token_urlsafe(48))"
    $template = Get-Content (Join-Path $Backend ".env.example") -Raw
    $content = $template -replace "(?m)^DOCPREDICT_SECRET_KEY=.*$", "DOCPREDICT_SECRET_KEY=$secret"
    [System.IO.File]::WriteAllText($EnvFile, $content, (New-Object System.Text.UTF8Encoding $false))
    Write-Host "Created backend\.env with a new random secret key"
} else { Write-Host "backend\.env already exists (left unchanged)" }

Step "Preparing the classifier"
$Model = Join-Path $Backend "ml\artifacts\model.joblib"
if ($Retrain -or -not (Test-Path $Model)) {
    Push-Location $Backend
    try { Invoke-Checked $VenvPython @("-m", "ml.train") } finally { Pop-Location }
} else { Write-Host "Model already trained (use -Retrain to rebuild it)" }

Step "Installing frontend dependencies"
Push-Location $Frontend
try {
    if (Test-Path "package-lock.json") { Invoke-Checked "npm.cmd" @("ci", "--no-audit", "--no-fund") }
    else { Invoke-Checked "npm.cmd" @("install", "--no-audit", "--no-fund") }
} finally { Pop-Location }

Step "Writing sample documents to .\samples"
Push-Location $Backend
try { Invoke-Checked $VenvPython @("-m", "tests.samples", (Join-Path $Root "samples")) | Out-Null } finally { Pop-Location }

Write-Host "`nSetup complete." -ForegroundColor Green
Write-Host "Start the app with:  powershell -ExecutionPolicy Bypass -File scripts\start.ps1"
