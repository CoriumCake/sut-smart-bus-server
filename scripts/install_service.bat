@echo off
:: =============================================================================
:: Install All Services - Run Once After Installing MongoDB & Mosquitto
:: =============================================================================

echo ============================================
echo  Installing SUT Smart Bus as Windows Service
echo ============================================
echo.

:: Check for Admin rights
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Please run this script as Administrator!
    pause
    exit /b 1
)

cd /d "%~dp0.."

:: Install NSSM (Non-Sucking Service Manager) for Python service
echo Downloading NSSM...
curl -L -o nssm.zip https://nssm.cc/release/nssm-2.24.zip
powershell -Command "Expand-Archive -Path nssm.zip -DestinationPath . -Force"
copy nssm-2.24\win64\nssm.exe C:\Windows\System32\nssm.exe
rmdir /s /q nssm-2.24
del nssm.zip

:: Create the FastAPI service
echo.
echo Creating SUT Smart Bus service...
set "SCRIPT_DIR=%~dp0.."
nssm install SutSmartBus "%SCRIPT_DIR%\venv\Scripts\python.exe"
nssm set SutSmartBus AppParameters "-m uvicorn app.main:app --host 0.0.0.0 --port 8000"
nssm set SutSmartBus AppDirectory "%SCRIPT_DIR%"
nssm set SutSmartBus DisplayName "SUT Smart Bus Server"
nssm set SutSmartBus Description "SUT Smart Bus API Server (FastAPI)"
nssm set SutSmartBus Start SERVICE_AUTO_START
nssm set SutSmartBus AppStdout "%SCRIPT_DIR%\logs\server.log"
nssm set SutSmartBus AppStderr "%SCRIPT_DIR%\logs\server_error.log"

echo.
echo ============================================
echo  Service installed!
echo ============================================
echo.
echo To start the service:
echo   net start SutSmartBus
echo.
echo To stop the service:
echo   net stop SutSmartBus
echo.
echo The server will now auto-start on Windows boot!
echo.
pause
