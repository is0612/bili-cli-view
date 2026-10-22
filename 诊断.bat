@echo off
rem Diagnostics report (ASCII-only: cmd.exe mis-parses UTF-8 batch files).
chcp 65001 >nul
setlocal
cd /d "%~dp0"
title bili-desk diagnosis

where node >nul 2>nul
if errorlevel 1 goto nonode

node "scripts\doctor.mjs"
pause
exit /b 0

:nonode
echo.
echo   Node.js is required (one-time install).
echo   Opening the download page ...
echo.
start "" "https://nodejs.org/zh-cn/download"
pause
exit /b 1
