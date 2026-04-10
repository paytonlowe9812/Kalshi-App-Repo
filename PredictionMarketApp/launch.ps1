# Start Kalshi Bot Builder: FastAPI (8000) + Vite dev server (5173)
# Usage:  .\launch.ps1
#         powershell -NoProfile -ExecutionPolicy Bypass -File .\launch.ps1

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$FrontendDir = Join-Path $Root "frontend"
$AppUrl = "http://localhost:5173/"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   Kalshi Bot Builder — Launching...   " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# ── Preflight checks ─────────────────────────────────────────────────────────

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: python not found on PATH. Install Python 3.10+ and retry." -ForegroundColor Red
    pause; exit 1
}

if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: npm not found on PATH. Install Node.js and retry." -ForegroundColor Red
    pause; exit 1
}

# Install frontend deps if node_modules is missing
$nodeModules = Join-Path $FrontendDir "node_modules"
if (-not (Test-Path $nodeModules)) {
    Write-Host "node_modules not found — running npm install..." -ForegroundColor Yellow
    Push-Location $FrontendDir
    npm install
    Pop-Location
    Write-Host "npm install complete." -ForegroundColor Green
}

# Quick check that the backend package is importable
$check = python -c "import fastapi, uvicorn" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Missing Python dependencies — running pip install..." -ForegroundColor Yellow
    python -m pip install -r (Join-Path $Root "requirements.txt") --quiet
    Write-Host "pip install complete." -ForegroundColor Green
}

# ── Free ports 8000 and 5173 ─────────────────────────────────────────────────

foreach ($port in @(8000, 5173)) {
    Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue |
        ForEach-Object {
            Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
        }
}
Start-Sleep -Seconds 1

# ── Launch backend ───────────────────────────────────────────────────────────

$backendCmd = @"
`$host.UI.RawUI.WindowTitle = 'Kalshi Backend :8000'
Set-Location -LiteralPath '$Root'
Write-Host ''
Write-Host '  Backend  http://127.0.0.1:8000' -ForegroundColor Cyan
Write-Host '  Press Ctrl+C to stop.' -ForegroundColor DarkGray
Write-Host ''
python -m uvicorn backend.main:app --reload --port 8000
Write-Host ''
Write-Host 'Backend stopped.' -ForegroundColor Yellow
pause
"@

Start-Process powershell.exe -ArgumentList @(
    "-NoExit", "-NoProfile", "-Command", $backendCmd
)

# Give uvicorn a moment to bind before starting the frontend
Start-Sleep -Seconds 3

# ── Launch frontend ──────────────────────────────────────────────────────────

$frontendCmd = @"
`$host.UI.RawUI.WindowTitle = 'Kalshi Frontend :5173'
Set-Location -LiteralPath '$FrontendDir'
Write-Host ''
Write-Host '  Frontend  http://localhost:5173' -ForegroundColor Cyan
Write-Host '  Press Ctrl+C to stop.' -ForegroundColor DarkGray
Write-Host ''
npm run dev
Write-Host ''
Write-Host 'Frontend stopped.' -ForegroundColor Yellow
pause
"@

Start-Process powershell.exe -ArgumentList @(
    "-NoExit", "-NoProfile", "-Command", $frontendCmd
)

# ── Open browser ─────────────────────────────────────────────────────────────

Start-Sleep -Seconds 4
Start-Process $AppUrl

# ── Done ─────────────────────────────────────────────────────────────────────

Write-Host ""
Write-Host "  Backend  -> http://127.0.0.1:8000" -ForegroundColor Green
Write-Host "  Frontend -> $AppUrl" -ForegroundColor Green
Write-Host ""
Write-Host "Two windows opened. Close them (Ctrl+C) to stop the app." -ForegroundColor DarkGray
Write-Host ""
