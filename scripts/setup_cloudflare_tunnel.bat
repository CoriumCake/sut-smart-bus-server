@echo off
:: =============================================================================
:: Cloudflare Tunnel Setup Script for SUT Smart Bus
:: =============================================================================
:: This script helps you set up Cloudflare Tunnel for public access
:: =============================================================================

echo ============================================
echo  Cloudflare Tunnel Setup
echo ============================================
echo.

:: Check for Admin rights
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Please run this script as Administrator!
    pause
    exit /b 1
)

:: Check if cloudflared is installed
cloudflared --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Cloudflared not found. Downloading...
    echo.
    
    :: Download cloudflared
    curl -L -o cloudflared.msi https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.msi
    
    if exist cloudflared.msi (
        echo Installing cloudflared...
        msiexec /i cloudflared.msi /quiet
        del cloudflared.msi
        
        :: Add to PATH
        setx PATH "%PATH%;C:\Program Files (x86)\cloudflared" /M
        echo Cloudflared installed!
    ) else (
        echo ERROR: Failed to download cloudflared.
        echo Please download manually from:
        echo https://github.com/cloudflare/cloudflared/releases
        pause
        exit /b 1
    )
)

echo.
echo ============================================
echo  Cloudflared is installed!
echo ============================================
echo.
echo Next steps:
echo.
echo 1. Login to Cloudflare:
echo    cloudflared tunnel login
echo.
echo 2. Create a tunnel:
echo    cloudflared tunnel create sutsmartbus
echo.
echo 3. Configure the tunnel (edit config.yml):
echo    See: C:\Users\%USERNAME%\.cloudflared\config.yml
echo.
echo 4. Route DNS (replace YOUR_TUNNEL_ID):
echo    cloudflared tunnel route dns sutsmartbus smartbus.yourdomain.com
echo    cloudflared tunnel route dns sutsmartbus mqtt.yourdomain.com
echo.
echo 5. Run the tunnel:
echo    cloudflared tunnel run sutsmartbus
echo.
echo 6. Or install as Windows service:
echo    cloudflared service install
echo    net start cloudflared
echo.
pause
