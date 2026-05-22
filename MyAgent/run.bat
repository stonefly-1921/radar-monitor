@echo off
cd /d "%~dp0"

echo ========================================
echo   MyAgent v2 - Double-click to launch
echo ========================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found
    pause
    exit /b 1
)

echo [OK] Python detected
echo.
echo ========================================
echo.

python agent\loop_v2.py %*

echo.
echo ========================================
echo   Done. Press any key to exit...
echo ========================================
pause >nul