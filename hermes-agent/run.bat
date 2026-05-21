@echo off
chcp 65001 >nul 2>&1
cd /d "%~dp0"

echo ========================================
echo Hermes Agent - Windows Launcher
echo ========================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.7+ or activate your conda environment.
    echo Tip: conda activate your_env_name
    pause
    exit /b 1
)

echo [OK] Python found
echo.

REM Check if dependencies are installed
python -c "import chardet" >nul 2>&1
if errorlevel 1 (
    echo [INFO] Installing dependencies...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Failed to install dependencies.
        pause
        exit /b 1
    )
    echo [OK] Dependencies installed
)

echo.
echo Starting Hermes Agent...
echo.
echo To use:
echo 1. Edit io\input.json with your task
echo 2. Press Enter to run
echo 3. Copy prompt.json content to your LLM web interface
echo 4. Paste the LLM response to io\response.json
echo 5. Press Enter to continue
echo.
echo ========================================
echo.

python agent\loop.py

echo.
echo ========================================
echo Agent stopped.
echo ========================================
pause
