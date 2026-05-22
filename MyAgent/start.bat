@echo off
:: Hermes Agent v2 - Quick Start
:: For Windows 7 and later
:: For air-gapped environments (no internet required)

setlocal enabledelayedexpansion

cd /d "%~dp0"

echo ================================================
echo   Hermes Agent - Quick Start
echo ================================================
echo.

:: Detect Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found!
    echo Please install Python 3.7+ from python.org
    echo Or activate your conda/virtual environment.
    echo.
    echo Example: conda activate hermes
    pause
    exit /b 1
)

echo [OK] Python detected

:: Check for v2 launcher (optimized version)
if exist "agent\loop_v2.py" (
    echo [OK] Hermes v2 detected
)

echo.
echo -----------------------------------------------
echo   USAGE INSTRUCTIONS (Air-Gapped Mode)
echo -----------------------------------------------
echo.
echo 1. Edit io\input.json - Write your task
echo    Example: {"content": "读取 README.md"}
echo.
echo 2. Run: python agent\loop_v2.py
echo.
echo 3. When prompted, copy io\prompt.json content
echo    to your web LLM interface (Open WebUI, etc.)
echo.
echo 4. Copy LLM response to io\response.json
echo.
echo 5. Press Enter to continue
echo.
echo -----------------------------------------------
echo.
echo Press Enter to start...
pause >nul

python agent\loop_v2.py

echo.
echo ================================================
echo   Hermes Agent Finished
echo ================================================
pause