@echo off
chcp 65001 >nul
title Project Analyzer - Logs Viewer
cls

cd /d "%~dp0"

echo ========================================
echo   PROJECT ANALYZER - LOGS VIEWER
echo ========================================
echo.

if not exist "analyzer.log" (
    echo [INFO] No log file found yet.
    echo [INFO] The log file will be created when you run the analyzer.
    echo.
    pause
    exit /b 0
)

echo [INFO] Showing last 50 lines of analyzer.log
echo [INFO] Press Ctrl+C to stop watching
echo.
echo ========================================
echo.

REM Показываем последние 50 строк
powershell -Command "Get-Content analyzer.log -Tail 50 -Wait"
