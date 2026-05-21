@echo off
setlocal

set "VSCMD="C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat""
if exist %VSCMD% (
    call %VSCMD%
) else (
    echo vcvars64.bat not found
    exit /b 1
)

set CL=/permissive- /EHsc /MD /O2 /W3
set CL=%CL% /DWSF_STATIC_DEFINE /DUT_STATIC_DEFINE
set CL=%CL% /I"D:\afsim-2.9.0-win64\swdev\src\core\wsf\source"
set CL=%CL% /I"D:\afsim-2.9.0-win64\swdev\src\core\wsf\source\observer"
set CL=%CL% /I"D:\afsim-2.9.0-win64\swdev\src\core\wsf\source\comm"
set CL=%CL% /I"D:\afsim-2.9.0-win64\swdev\src\core\wsf_util\source"
set CL=%CL% /I"D:\afsim-2.9.0-win64\swdev\BUILD\wsf\source"
set CL=%CL% /I"D:\afsim-2.9.0-win64\swdev\BUILD\wsf\source\include"
set CL=%CL% /I"D:\afsim-2.9.0-win64\swdev\BUILD\util\source"
set CL=%CL% /I"D:\afsim-2.9.0-win64\swdev\src\tools\util\source"
set CL=%CL% /I"D:\afsim-2.9.0-win64\swdev\src\tools\util_script\source"
set CL=%CL% /I"D:\afsim-2.9.0-win64\swdev\BUILD"
set CL=%CL% /I"D:\afsim-2.9.0-win64\swdev\BUILD\build_wsf_fires"
set CL=%CL% /I"D:\afsim-2.9.0-win64\swdev\BUILD\util_script\source"
set CL=%CL% /I"D:\afsim-2.9.0-win64\swdev\BUILD\include"
set CL=%CL% /I"D:\afsim-2.9.0-win64\swdev\src\tools\dis\source"

set SRC_DIR=C:\Users\15041\.openclaw\workspace\kill-chain-sim\src\core\wsf_shm\source
set BUILD_DIR=C:\Users\15041\.openclaw\workspace\kill-chain-sim\src\core\wsf_shm\build

if not exist "%BUILD_DIR%" mkdir "%BUILD_DIR%"

set OBJECTS=

for %%F in (
    "%SRC_DIR%\wsf_plugin_entry.cpp"
    "%SRC_DIR%\WsfShmScenarioExtension.cpp"
    "%SRC_DIR%\WsfShmSimulationExtension.cpp"
) do (
    if exist %%F (
        echo Compiling: %%~nxF
        set OBJ=!BUILD_DIR!\%%~nF.o
        cl /c %CL% /Fo"!OBJ!" %%F >> build_msvc.log 2>&1
        if errorlevel 1 (
            echo FAILED: %%~nxF
            type build_msvc.log
            exit /b 1
        )
        set OBJECTS=!OBJECTS! !OBJ!
    ) else (
        echo Not found: %%F
    )
)

echo Linking DLL...
set DLL=!BUILD_DIR!\wsf_shm.dll
link /DLL /OUT:"!DLL!" !OBJECTS! /LIBPATH:"D:\afsim-2.9.0-win64\swdev\BUILD\lib" ws2_32.lib psapi.lib <<-LinkFlags
/IGNORE:4217 /IGNORE:4199
LinkFlags

if errorlevel 1 (
    echo LINK FAILED
    exit /b 1
)

echo.
echo DLL built: !DLL!
dir /b /o:n "!DLL!"
echo.
echo Verifying exports:
dumpbin /EXPORTS "!DLL!" | findstr /i "WSF wsf"
