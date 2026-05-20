@echo off
rem build_wsf_shm.bat - Build wsf_shm.dll on Windows
rem Usage: build_wsf_shm.bat

set CC=D:\anaconda3\Library\bin\gcc.exe
set SRC_DIR=%~dp0
set DEST=D:\afsim-2.9.0-win64\bin\wsf_plugins
set SRC_FILE=%SRC_DIR%wsf_shm.c

if not exist "%SRC_FILE%" (
    echo ERROR: Source not found: %SRC_FILE%
    exit /b 1
)

if not exist "%DEST%" mkdir "%DEST%"

echo Building wsf_shm.dll...
"%CC%" -shared -o "%DEST%\wsf_shm.dll" "%SRC_FILE%" -DBUILD_DLL=1 -O2 -Wl,--out-implib,"%DEST%\wsf_shm.lib"
if errorlevel 1 (
    echo ERROR: Build failed
    exit /b 1
)

echo SUCCESS: %DEST%\wsf_shm.dll
dir "%DEST%\wsf_shm.dll"
