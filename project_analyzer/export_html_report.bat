@echo off
chcp 65001 >nul
title Export HTML Report
cls

echo ========================================
echo   EXPORT HTML REPORT
echo ========================================
echo.

REM Получаем последний project_id из логов
for /f "tokens=*" %%i in ('powershell -Command "Select-String -Path analyzer.log -Pattern 'project_id: ([a-f0-9-]+)' | Select-Object -Last 1 | ForEach-Object { $_.Matches.Groups[1].Value }"') do set PROJECT_ID=%%i

if "%PROJECT_ID%"=="" (
    echo [ERROR] No project_id found in logs
    echo Please run an analysis first
    pause
    exit /b 1
)

echo Found project_id: %PROJECT_ID%
echo.
echo Downloading results...

REM Скачиваем JSON результаты
powershell -Command "Invoke-WebRequest -Uri 'http://localhost:8000/results/%PROJECT_ID%' -Out results_temp.json"

if not exist results_temp.json (
    echo [ERROR] Failed to download results
    pause
    exit /b 1
)

echo.
echo Generating HTML report...

REM Генерируем HTML отчет
python generate_report.py results_temp.json analysis_report.html

if exist analysis_report.html (
    echo.
    echo [SUCCESS] HTML report generated!
    echo.
    echo Opening in browser...
    start analysis_report.html
) else (
    echo [ERROR] Failed to generate HTML report
)

echo.
pause
