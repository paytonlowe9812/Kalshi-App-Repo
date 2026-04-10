# One-step setup: Python venv, pip dependencies, frontend npm install, launch script generation.
# Run from the PredictionMarketApp folder (same folder as backend/ and frontend/).

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
Set-Location $Root

function Get-InstallerPython {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        $exe = & py -3 -c "import sys; print(sys.executable)" 2>$null
        if ($LASTEXITCODE -eq 0 -and $exe) { return $exe.Trim() }
    }
    foreach ($name in @("python", "python3")) {
        if (Get-Command $name -ErrorAction SilentlyContinue) {
            return (Get-Command $name).Source
        }
    }
    return $null
}

Write-Host ""
Write-Host "Kalshi Bot Builder — install" -ForegroundColor Cyan
Write-Host ""

$pyExe = Get-InstallerPython
if (-not $pyExe) {
    Write-Host "ERROR: Python 3.10+ not found. Install from https://www.python.org/downloads/ and retry." -ForegroundColor Red
    exit 1
}

if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: npm not found. Install Node.js LTS from https://nodejs.org/ and retry." -ForegroundColor Red
    exit 1
}

$venvDir = Join-Path $Root ".venv"
$venvPy = Join-Path $Root ".venv\Scripts\python.exe"
if (Test-Path $venvPy) {
    Write-Host "Using existing .venv ..." -ForegroundColor DarkGray
} else {
    Write-Host "Creating virtual environment..." -ForegroundColor DarkGray
    & $pyExe -m venv $venvDir
}

Write-Host "Installing Python packages..." -ForegroundColor DarkGray
& $venvPy -m pip install --upgrade pip -q
& $venvPy -m pip install -r (Join-Path $Root "requirements.txt")

Write-Host "Installing frontend (npm)..." -ForegroundColor DarkGray
Push-Location (Join-Path $Root "frontend")
npm install
Pop-Location

Write-Host ""
Write-Host "Install finished." -ForegroundColor Green
Write-Host "Start the app:  .\launch.ps1   or   launch.bat" -ForegroundColor Green
Write-Host ""
