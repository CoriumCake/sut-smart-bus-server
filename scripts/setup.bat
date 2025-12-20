@echo off
echo ========================================
echo   SUT Smart Bus Server - Windows Setup
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH!
    echo Please install Python 3.10+ from https://python.org
    pause
    exit /b 1
)

echo [1/4] Creating virtual environment...
python -m venv venv
call venv\Scripts\activate

echo [2/4] Installing dependencies...
pip install -r requirements.txt

echo [3/4] Installing telemetry dependencies...
pip install -r telemetry\requirements.txt

echo [4/4] Creating .env file from template...
if not exist .env (
    copy .env.example .env
    echo [!] Created .env file - please edit with your settings!
) else (
    echo [OK] .env file already exists
)

echo.
echo ========================================
echo   Setup complete!
echo ========================================
echo.
echo Next steps:
echo   1. Edit .env with your MongoDB and MQTT settings
echo   2. Run start_server.bat to start the server
echo.
pause
