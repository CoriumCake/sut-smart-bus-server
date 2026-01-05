@echo off
:: =============================================================================
:: SUT Smart Bus Server - Stop Script
:: =============================================================================

echo ============================================
echo  Stopping SUT Smart Bus Server
echo ============================================
echo.

:: Kill Python/Uvicorn processes
echo Stopping FastAPI server...
taskkill /F /IM python.exe >nul 2>&1
taskkill /F /IM uvicorn.exe >nul 2>&1

echo.
echo Server stopped!
echo.
echo Note: MongoDB and Mosquitto services are still running.
echo To stop them too, run:
echo   net stop MongoDB
echo   net stop Mosquitto
echo.
pause
