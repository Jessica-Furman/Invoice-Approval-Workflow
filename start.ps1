# InVoicee dev launcher — starts backend + frontend in separate windows and opens the browser.
# Usage:  right-click > "Run with PowerShell", or in a terminal:  ./start.ps1
$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

# Ensure Node (installed user-scope via winget) is on PATH for this session.
$nodeDir = "$env:LOCALAPPDATA\Microsoft\WinGet\Packages\OpenJS.NodeJS.LTS_Microsoft.Winget.Source_8wekyb3d8bbwe\node-v24.16.0-win-x64"
if (Test-Path $nodeDir) { $env:Path = "$nodeDir;$env:Path" }

Write-Host "Starting backend (http://localhost:8000) ..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList @(
  "-NoExit","-Command",
  "cd '$root\backend'; .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000"
)

Write-Host "Starting frontend (http://localhost:5173) ..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList @(
  "-NoExit","-Command",
  "`$env:Path='$nodeDir;'+`$env:Path; cd '$root\frontend'; npm run dev"
)

Start-Sleep -Seconds 6
Start-Process "http://localhost:5173"
Write-Host "Launched. Two terminal windows are now running the servers." -ForegroundColor Green
