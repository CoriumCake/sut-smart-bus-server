@echo off
echo ========================================
echo   Starting SUT Smart Bus Server (Anaconda)
echo ========================================
echo.

:: Initialize Conda
call C:\ProgramData\anaconda3\Scripts\activate.bat
call conda activate sutbus

:: Get script directory and move to project root
set SCRIPT_DIR=%~dp0
cd /d %SCRIPT_DIR%..

echo [1/2] Starting Main Server on port 8000...
start "SUT-Server" cmd /k "call C:\ProgramData\anaconda3\Scripts\activate.bat && conda activate sutbus && uvicorn app.main:app --host 0.0.0.0 --port 8000"

timeout /t 3 /nobreak >nul

echo [2/2] Starting Telemetry Service...
start "SUT-Telemetry" cmd /k "call C:\ProgramData\anaconda3\Scripts\activate.bat && conda activate sutbus && cd %SCRIPT_DIR%..\telemetry && python main.py"

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
