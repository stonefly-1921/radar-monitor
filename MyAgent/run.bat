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

rem ========================================
rem Clear IO files before starting
rem ========================================
echo.
echo [CLEAN] Clearing IO files...
if exist "io\input.txt" echo. > "io\input.txt"
if exist "io\prompt.txt" echo. > "io\prompt.txt"
if exist "io\response.txt" echo. > "io\response.txt"
if exist "io\tool_result.json" echo. > "io\tool_result.json"
if exist "io\memory.json" (
    rem Keep memory.json - only clear session-related files
    echo. > "io\memory.json"
)
echo [CLEAN] Done
echo.

echo ========================================
echo.

python agent\loop_v2.py %*

echo.
echo ========================================
echo   Done. Press any key to exit...
echo ========================================
pause >nul