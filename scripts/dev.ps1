# 开发模式：后端 8811 + 前端 5199，两个窗口
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent

$py = Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path $py)) { throw "先建 venv：uv venv .venv; uv pip install -r backend/requirements.txt" }

Write-Host "[dev] 后端 http://127.0.0.1:8811"
Start-Process -FilePath $py -WorkingDirectory (Join-Path $root 'backend') `
  -ArgumentList '-m', 'uvicorn', 'app.main:app', '--port', '8811', '--reload' -WindowStyle Minimized

Start-Sleep -Seconds 2
Write-Host "[dev] 前端 http://127.0.0.1:5199"
Start-Process -FilePath 'npm.cmd' -WorkingDirectory $root -ArgumentList 'run', 'dev' -WindowStyle Minimized

Start-Sleep -Seconds 3
Start-Process 'http://127.0.0.1:5199/'
