@echo off
echo ========================================
echo   Stopping SUT Smart Bus Services
echo ========================================
echo.

taskkill /FI "WINDOWTITLE eq SUT-Server*" /F 2>nul
if %errorlevel% equ 0 (
    echo [OK] Main Server stopped
) else (
    echo [--] Main Server was not running
)

taskkill /FI "WINDOWTITLE eq SUT-Telemetry*" /F 2>nul
if %errorlevel% equ 0 (
    echo [OK] Telemetry Service stopped
) else (
    echo [--] Telemetry Service was not running
)

echo.
echo All services stopped.
pause
