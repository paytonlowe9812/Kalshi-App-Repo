# Start Kalshi Bot Builder: FastAPI (8000) + Vite (5173) in separate consoles.
# Usage: .\launch.ps1   or   powershell -NoProfile -ExecutionPolicy Bypass -File .\launch.ps1

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot

$ports = @(8000, 5173)
foreach ($port in $ports) {
    Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue |
        ForEach-Object {
            Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
        }
}

Start-Sleep -Seconds 1

$backendCmd = @"
Set-Location -LiteralPath '$Root'
Write-Host 'Backend: http://127.0.0.1:8000' -ForegroundColor Cyan
python -m uvicorn backend.main:app --reload --port 8000
"@

$frontendCmd = @"
Set-Location -LiteralPath '$Root\frontend'
Write-Host 'Frontend: http://localhost:5173/' -ForegroundColor Cyan
npm run dev
"@

Start-Process -FilePath "powershell.exe" -WorkingDirectory $Root -ArgumentList @(
    "-NoExit", "-NoProfile", "-Command", $backendCmd
)

Start-Sleep -Seconds 2

Start-Process -FilePath "powershell.exe" -WorkingDirectory $Root -ArgumentList @(
    "-NoExit", "-NoProfile", "-Command", $frontendCmd
)

Write-Host "Opened two windows: backend (uvicorn) and frontend (vite)." -ForegroundColor Green
Write-Host "App URL: http://localhost:5173/" -ForegroundColor Green
