@echo off
chcp 65001 >nul 2>&1
cd /d "%~dp0"

echo ========================================
echo   MyAgent - 双击启动
echo ========================================
echo.

REM 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python 未找到，请先安装 Python 3.7+
    pause
    exit /b 1
)

REM 解析参数
set MODE=normal
if "%~1"=="--new" set MODE=new
if "%~1"=="-n" set MODE=new

if "%MODE%"=="new" (
    echo [NEW] 模式：清除所有历史记录
) else (
    echo [提示] 用 --new 参数可清除历史记录
)

echo.
echo ========================================
echo.

python agent\loop_v2.py %*

echo.
echo ========================================
echo   执行完毕，按任意键退出...
echo ========================================
pause >nul
