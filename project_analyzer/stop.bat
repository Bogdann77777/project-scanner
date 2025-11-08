@echo off
chcp 65001 >nul
cls
echo ========================================
echo   PROJECT ANALYZER - STOPPING SERVER
echo ========================================
echo.

REM Убиваем все процессы Python (Flask)
echo [INFO] Stopping Flask server...
taskkill /F /IM python.exe /FI "WINDOWTITLE eq *app.py*" 2>nul

REM Альтернативный метод - убиваем все Python процессы на порту 8000
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do (
    echo [INFO] Killing process on port 8000 (PID: %%a)
    taskkill /F /PID %%a 2>nul
)

echo.
echo [SUCCESS] Server stopped!
echo.
pause
