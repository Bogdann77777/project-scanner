@echo off
chcp 65001 >nul
title Clear Logs
cls

cd /d "%~dp0"

echo ========================================
echo   CLEAR ANALYZER LOGS
echo ========================================
echo.

if exist "analyzer.log" (
    del analyzer.log
    echo [SUCCESS] Log file deleted!
) else (
    echo [INFO] No log file found.
)

echo.
pause
