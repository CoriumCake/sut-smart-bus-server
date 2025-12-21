@echo off
echo ========================================
echo   SUT Smart Bus - Anaconda Setup
echo ========================================
echo.

:: Initialize Conda
call C:\ProgramData\anaconda3\Scripts\activate.bat

echo [1/4] Creating conda environment 'sutbus'...
call conda create -n sutbus python=3.10 -y

echo [2/4] Activating environment...
call conda activate sutbus

echo [3/4] Installing main server dependencies...
cd /d %~dp0..
pip install -r requirements.txt

echo [4/4] Installing telemetry dependencies...
pip install -r telemetry\requirements.txt

echo.
echo ========================================
echo   Setup Complete!
echo ========================================
echo.
echo   Environment: sutbus
echo   Python: 3.10
echo.
echo   Next: Edit .env file, then run start_server.bat
echo ========================================
pause