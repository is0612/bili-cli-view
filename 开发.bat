@echo off
rem Dev-mode launcher (hot reload). ASCII-only on purpose: cmd.exe mis-parses UTF-8 batch files.
chcp 65001 >nul
setlocal
cd /d "%~dp0"
title bili-desk dev

where node >nul 2>nul
if errorlevel 1 goto nonode

node "scripts\dev.mjs" %*
if errorlevel 1 pause
exit /b 0

:nonode
rem Chinese message + download link are printed by the .ps1 (UTF-8 with BOM).
powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\no-node.ps1"
exit /b 1
