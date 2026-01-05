@echo off
:: =============================================================================
:: SUT Smart Bus Server - Start Script
:: =============================================================================

echo ============================================
echo  Starting SUT Smart Bus Server
echo ============================================
echo.

cd /d "%~dp0.."

:: Start MongoDB if not running
echo [1/3] Checking MongoDB...
sc query MongoDB | find "RUNNING" >nul 2>&1
if %errorlevel% neq 0 (
    echo Starting MongoDB...
    net start MongoDB >nul 2>&1
)
echo MongoDB: OK

:: Start Mosquitto if not running
echo [2/3] Checking Mosquitto...
sc query Mosquitto | find "RUNNING" >nul 2>&1
if %errorlevel% neq 0 (
    echo Starting Mosquitto...
    net start Mosquitto >nul 2>&1
)
echo Mosquitto: OK

:: Activate venv and start server
echo [3/3] Starting FastAPI server...
call venv\Scripts\activate.bat

echo.
echo ============================================
echo  Server starting on http://0.0.0.0:8000
echo  Dashboard: http://localhost:8000/dashboard
echo  API Docs:  http://localhost:8000/docs
echo ============================================
echo  Press Ctrl+C to stop the server
echo ============================================
echo.

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
