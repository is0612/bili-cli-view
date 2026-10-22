# 生产模式：先构建，再由 FastAPI 单端口托管（8811）
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent

$py = Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path $py)) { throw "先建 venv：uv venv .venv; uv pip install -r backend/requirements.txt" }

Push-Location $root
try {
  if (-not (Test-Path (Join-Path $root 'dist'))) {
    Write-Host "[serve] 没有 dist，先构建"
    npm run build
  }
} finally {
  Pop-Location
}

Write-Host "[serve] http://127.0.0.1:8811"
Start-Process -FilePath $py -WorkingDirectory (Join-Path $root 'backend') `
  -ArgumentList '-m', 'uvicorn', 'app.main:app', '--port', '8811'
Start-Sleep -Seconds 3
Start-Process 'http://127.0.0.1:8811/'
