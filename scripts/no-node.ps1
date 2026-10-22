# 没装 Node.js 时给不懂命令行的人看的提示。
# 注意：这个文件必须存成 UTF-8 带 BOM，Windows PowerShell 5.1 才不会把中文读成乱码。
param([switch]$NoOpen)

Write-Host ''
Write-Host '  这台电脑还没装 Node.js（只需要装一次）。' -ForegroundColor Yellow
Write-Host ''
Write-Host '  接下来会自动打开下载页：'
Write-Host '    1. 选 LTS 版本下载；'
Write-Host '    2. 安装时一路点「下一步」，不用改任何选项；'
Write-Host '    3. 装完回到这里，重新双击「启动.bat」。'
Write-Host ''

if (-not $NoOpen) {
  Start-Process 'https://nodejs.org/zh-cn/download'
  Read-Host '  按回车关闭这个窗口'
}
