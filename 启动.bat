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
rem Chinese message + download link are printed by the .ps1 (UTF-8 with BOM).
powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\no-node.ps1"
exit /b 1
