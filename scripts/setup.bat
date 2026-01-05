@echo off
:: =============================================================================
:: SUT Smart Bus Server - Complete Setup Script
:: =============================================================================
:: Run this script as Administrator
:: =============================================================================

echo ============================================
echo  SUT Smart Bus Server - Setup Script
echo ============================================
echo.

:: Check for Admin rights
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Please run this script as Administrator!
    echo Right-click and select "Run as administrator"
    pause
    exit /b 1
)

:: Create directories
echo [1/6] Creating directories...
if not exist "C:\SutSmartBus" mkdir "C:\SutSmartBus"
if not exist "C:\SutSmartBus\logs" mkdir "C:\SutSmartBus\logs"
if not exist "C:\SutSmartBus\data" mkdir "C:\SutSmartBus\data"

:: Check Python
echo [2/6] Checking Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python not found! Please install Python 3.10+ first.
    echo Download from: https://www.python.org/downloads/
    pause
    exit /b 1
)
echo Python found!

:: Setup Python virtual environment
echo [3/6] Setting up Python environment...
cd /d "%~dp0"
if not exist "venv" (
    python -m venv venv
)
call venv\Scripts\activate.bat
pip install -r requirements.txt --quiet

:: Create .env if not exists
echo [4/6] Checking configuration...
if not exist ".env" (
    copy ".env.example" ".env"
    echo Created .env file - please edit with your settings!
)

:: Check MongoDB
echo [5/6] Checking MongoDB...
sc query MongoDB >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo WARNING: MongoDB service not found!
    echo Please install MongoDB Community Server:
    echo https://www.mongodb.com/try/download/community
    echo.
) else (
    net start MongoDB >nul 2>&1
    echo MongoDB is ready!
)

:: Check Mosquitto
echo [6/6] Checking Mosquitto...
sc query Mosquitto >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo WARNING: Mosquitto service not found!
    echo Please install Mosquitto MQTT Broker:
    echo https://mosquitto.org/download/
    echo.
) else (
    net start Mosquitto >nul 2>&1
    echo Mosquitto is ready!
)

echo.
echo ============================================
echo  Setup Complete!
echo ============================================
echo.
echo Next steps:
echo   1. Install MongoDB if not installed
echo   2. Install Mosquitto if not installed
echo   3. Edit .env with your settings
echo   4. Run: start_server.bat
echo.
pause
