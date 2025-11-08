@echo off
REM ===== САМЫЙ ПРОСТОЙ ЗАПУСК =====
REM Просто запускает сервер без проверок

cd /d "%~dp0"

echo Starting Project Analyzer...
echo.

REM Создаем .env если его нет
if not exist ".env" copy .env.example .env >nul 2>&1

REM Запускаем сервер в отдельном окне
start "Project Analyzer Server" cmd /k "python ui/app.py"

REM Ждем и открываем браузер
timeout /t 3 /nobreak >nul
start http://localhost:8000

echo.
echo Server started! Browser should open automatically.
echo Close the server window to stop.
echo.
