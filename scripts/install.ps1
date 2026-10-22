# 换台电脑：一条命令把环境装起来并起服务（等价于双击 启动.bat）
#   powershell -ExecutionPolicy Bypass -File scripts/install.ps1
#
# 真正干活的是 scripts/setup.mjs + scripts/start.mjs：
# 没装 uv 会自动下载、没装 Python 会自动下 3.12、依赖没装会自己装。
# 这个脚本留着，是给不习惯双击的人一个命令行入口。
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root

if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
  throw @'
缺 Node.js（脚本本身要用它跑）。

装一个再回来：https://nodejs.org/zh-cn/download
一路「下一步」即可，装完重开一个 PowerShell 窗口。
'@
}

node scripts\start.mjs
exit $LASTEXITCODE
