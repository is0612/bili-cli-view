@echo off
rem One-click launcher. All Chinese messages live in Node (UTF-8 safe);
rem this file stays ASCII-only because cmd.exe mis-parses UTF-8 batch files.
chcp 65001 >nul
setlocal
cd /d "%~dp0"
title bili-desk

where node >nul 2>nul
if errorlevel 1 goto nonode

node "scripts\start.mjs" %*
if errorlevel 1 pause
exit /b 0

:nonode
echo.
echo   Node.js is required (one-time install).
echo   Opening the download page ...
echo.
start "" "https://nodejs.org/zh-cn/download"
echo   Install it with the default options, then run this file again.
pause
exit /b 1
