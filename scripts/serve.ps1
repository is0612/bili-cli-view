# 生产模式：构建 dist 并由 FastAPI 单端口托管（8811）
# 和「启动.bat」做的是同一件事，这里保留一个 PowerShell 入口。
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root
node scripts\start.mjs
exit $LASTEXITCODE
