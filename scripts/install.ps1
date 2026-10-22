# 换台电脑：一条命令把环境装起来（Windows / PowerShell）
#   powershell -ExecutionPolicy Bypass -File scripts/install.ps1
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root

function Need($name, $hint) {
  if (-not (Get-Command $name -ErrorAction SilentlyContinue)) { throw "缺 $name：$hint" }
}

Need 'uv' '先装 uv：irm https://astral.sh/uv/install.ps1 | iex'
if (-not (Test-Path (Join-Path $root 'node_modules'))) {
  Need 'npm' '前端依赖要 node/npm；只想用生产构建可以跳过 npm，直接放 dist/'
}

Write-Host '[1/4] 建 venv …'
if (-not (Test-Path (Join-Path $root '.venv'))) { uv venv .venv --python 3.12 }

Write-Host '[2/4] 装后端依赖 + bili-cli（装进项目 venv，不污染全局）…'
uv pip install --python (Join-Path $root '.venv\Scripts\python.exe') -r backend/requirements.txt

Write-Host '[3/4] 装前端依赖并构建 …'
if (-not (Test-Path (Join-Path $root 'node_modules'))) { npm install }
npm run build

Write-Host '[4/4] 起服务 …'
$py = Join-Path $root '.venv\Scripts\python.exe'
$bili = Join-Path $root '.venv\Scripts\bili.exe'
Write-Host "  bili : $bili"
Write-Host "  面板 : http://127.0.0.1:8811/  （第一次要扫码登录）"
Start-Process -FilePath $py -WorkingDirectory (Join-Path $root 'backend') `
  -ArgumentList '-m', 'uvicorn', 'app.main:app', '--port', '8811'
Start-Sleep -Seconds 3
Start-Process 'http://127.0.0.1:8811/'
