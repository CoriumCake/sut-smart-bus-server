@echo off
echo ========================================
echo   Starting SUT Smart Bus Server
echo ========================================
echo.

REM Get script directory
set SCRIPT_DIR=%~dp0
set PROJECT_DIR=%SCRIPT_DIR%..

cd /d %PROJECT_DIR%

REM Activate virtual environment
if exist venv\Scripts\activate (
    call venv\Scripts\activate
) else (
    echo [ERROR] Virtual environment not found!
    echo Please run setup.bat first.
    pause
    exit /b 1
)

echo Starting Main Server on port 8000...
start "SUT-Server" cmd /k "cd /d %PROJECT_DIR% && venv\Scripts\uvicorn app.main:app --host 0.0.0.0 --port 8000"

timeout /t 3 /nobreak >nul

echo Starting Telemetry Service...
start "SUT-Telemetry" cmd /k "cd /d %PROJECT_DIR%\telemetry && ..\venv\Scripts\python main.py"

echo.
echo ========================================
echo   Services Started!
echo ========================================
echo.
echo   Main Server: http://localhost:8000
echo   API Docs:    http://localhost:8000/docs
echo   Dashboard:   http://localhost:8000/dashboard
echo.
echo   To stop: close the server windows or run stop_server.bat
echo ========================================
pause
