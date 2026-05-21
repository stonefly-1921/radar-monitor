@echo off
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"

set CL=/EHsc /MD /O2 /W3 /WX- /c /nologo
set CL=%CL% /DWSF_STATIC_DEFINE /DUT_STATIC_DEFINE
set CL=%CL% /DWIN32 /D_WIN32 /D_WIN64 /DNDEBUG
set CL=%CL% /D_SCL_SECURE_NO_WARNINGS /D_CRT_SECURE_NO_WARNINGS /D_CRT_NONSTDC_NO_WARNINGS
set CL=%CL% /I"D:\afsim-2.9.0-win64\swdev\src\wsf_plugins\wsf_shm\source"
set CL=%CL% /I"D:\afsim-2.9.0-win64\swdev\BUILD\build_wsf_fires"
set CL=%CL% /I"D:\afsim-2.9.0-win64\swdev\BUILD\wsf\source\include"
set CL=%CL% /I"D:\afsim-2.9.0-win64\swdev\src\core\wsf\source"
set CL=%CL% /I"D:\afsim-2.9.0-win64\swdev\src\core\wsf\source\comm"
set CL=%CL% /I"D:\afsim-2.9.0-win64\swdev\src\core\wsf\source\event_pipe"
set CL=%CL% /I"D:\afsim-2.9.0-win64\swdev\src\core\wsf\source\mover"
set CL=%CL% /I"D:\afsim-2.9.0-win64\swdev\src\core\wsf\source\observer"
set CL=%CL% /I"D:\afsim-2.9.0-win64\swdev\src\core\wsf\source\processor"
set CL=%CL% /I"D:\afsim-2.9.0-win64\swdev\src\core\wsf\source\sensor"
set CL=%CL% /I"D:\afsim-2.9.0-win64\swdev\BUILD\wsf\source"
set CL=%CL% /I"D:\afsim-2.9.0-win64\swdev\BUILD"
set CL=%CL% /I"D:\afsim-2.9.0-win64\swdev\BUILD\include"
set CL=%CL% /I"D:\afsim-2.9.0-win64\swdev\src\tools\util\source"
set CL=%CL% /I"D:\afsim-2.9.0-win64\swdev\BUILD\util\source"
set CL=%CL% /I"D:\afsim-2.9.0-win64\swdev\src\tools\util_script\source"
set CL=%CL% /I"D:\afsim-2.9.0-win64\swdev\BUILD\util_script"
set CL=%CL% /I"D:\afsim-2.9.0-win64\swdev\BUILD\util_script\source"
set CL=%CL% /I"D:\afsim-2.9.0-win64\swdev\src\tools\geodata\source"
set CL=%CL% /I"D:\afsim-2.9.0-win64\swdev\BUILD\geodata\source"
set CL=%CL% /I"D:\afsim-2.9.0-win64\swdev\src\tools\genio\source"
set CL=%CL% /I"D:\afsim-2.9.0-win64\swdev\BUILD\genio"
set CL=%CL% /I"D:\afsim-2.9.0-win64\swdev\src\tools\packetio\source"
set CL=%CL% /I"D:\afsim-2.9.0-win64\swdev\BUILD\packetio"
set CL=%CL% /I"D:\afsim-2.9.0-win64\swdev\src\tools\dis\source"
set CL=%CL% /I"D:\afsim-2.9.0-win64\swdev\BUILD\dis"
set CL=%CL% /I"D:\afsim-2.9.0-win64\swdev\src\tools\tracking_filters\source"
set CL=%CL% /I"D:\afsim-2.9.0-win64\swdev\BUILD\tracking_filters"
set CL=%CL% /I"D:\afsim-2.9.0-win64\swdev\BUILD\tracking_filters\source"
set CL=%CL% /I"D:\afsim-2.9.0-win64\swdev\src\tools\profiling\source"
set CL=%CL% /I"D:\afsim-2.9.0-win64\swdev\BUILD\profiling\source"
set CL=%CL% /I"D:\afsim-2.9.0-win64\swdev\src\core\wsf_util\source"
set CL=%CL% /I"D:\afsim-2.9.0-win64\swdev\src\core\wsf_mil\source"
set CL=%CL% /I"D:\afsim-2.9.0-win64\swdev\src\core\wsf_mil\source\comm"
set CL=%CL% /I"D:\afsim-2.9.0-win64\swdev\src\core\wsf_mil\source\ew"
set CL=%CL% /I"D:\afsim-2.9.0-win64\swdev\src\core\wsf_mil\source\mover"
set CL=%CL% /I"D:\afsim-2.9.0-win64\swdev\src\core\wsf_mil\source\processor"
set CL=%CL% /I"D:\afsim-2.9.0-win64\swdev\src\core\wsf_mil\source\observer"
set CL=%CL% /I"D:\afsim-2.9.0-win64\swdev\src\core\wsf_mil\source\script"
set CL=%CL% /I"D:\afsim-2.9.0-win64\swdev\src\core\wsf_mil\source\sensor"
set CL=%CL% /I"D:\afsim-2.9.0-win64\swdev\src\core\wsf_mil\source\weapon"
set CL=%CL% /I"D:\afsim-2.9.0-win64\swdev\BUILD\build_wsf_mil\source"

set SRC_DIR=C:\Users\15041\.openclaw\workspace\kill-chain-sim\src\core\wsf_shm\source
set BUILD_DIR=C:\Users\15041\.openclaw\workspace\kill-chain-sim\src\core\wsf_shm\build
set LOG=%BUILD_DIR%\build_msvc.log
set LIBS=D:\afsim-2.9.0-win64\swdev\BUILD\lib\Release

if not exist "%BUILD_DIR%" mkdir "%BUILD_DIR%"
del /f /q "%LOG%" 2>nul

echo === Compiling WsfShmScenarioExtension ===
cl.exe %CL% /Fo"%BUILD_DIR%\WsfShmScenarioExtension.obj" "%SRC_DIR%\WsfShmScenarioExtension.cpp" > "%LOG%" 2>&1
if errorlevel 1 (
    echo FAILED: WsfShmScenarioExtension
    type "%LOG%"
    exit /b 1
)
echo OK: WsfShmScenarioExtension

echo === Compiling WsfShmSimulationExtension ===
cl.exe %CL% /Fo"%BUILD_DIR%\WsfShmSimulationExtension.obj" "%SRC_DIR%\WsfShmSimulationExtension.cpp" >> "%LOG%" 2>&1
if errorlevel 1 (
    echo FAILED: WsfShmSimulationExtension
    type "%LOG%"
    exit /b 1
)
echo OK: WsfShmSimulationExtension

echo === Compiling wsf_shm.c ===
cl.exe %CL% /Fo"%BUILD_DIR%\wsf_shm.obj" "%SRC_DIR%\wsf_shm.c" >> "%LOG%" 2>&1
if errorlevel 1 (
    echo FAILED: wsf_shm.c
    type "%LOG%"
    exit /b 1
)
echo OK: wsf_shm.c

echo.
echo === Linking DLL ===
link /DLL /DEF:"%SRC_DIR%\wsf_shm.def" /OUT:"%BUILD_DIR%\wsf_shm.dll" ^
  "%BUILD_DIR%\WsfShmScenarioExtension.obj" ^
  "%BUILD_DIR%\WsfShmSimulationExtension.obj" ^
  "%BUILD_DIR%\wsf_shm.obj" ^
  /LIBPATH:"%LIBS%" ^
  ut.lib wsf.lib wsf_util.lib util.lib genio.lib dis.lib packetio.lib geodata.lib ^
  util_script.lib tracking_filters.lib profiling.lib wsf_mil.lib ^
  ws2_32.lib psapi.lib ^
  kernel32.lib user32.lib gdi32.lib winspool.lib shell32.lib ole32.lib oleaut32.lib uuid.lib comdlg32.lib advapi32.lib ^
  /LIBPATH:"C:\Program Files (x86)\Windows Kits\10\Lib\10.0.26100.0\ucrt\x64" ^
  /LIBPATH:"C:\Program Files (x86)\Windows Kits\10\Lib\10.0.26100.0\um\x64" ^
  /IGNORE:4217 /IGNORE:4199 >> "%LOG%" 2>&1
if errorlevel 1 (
    echo LINK FAILED
    type "%LOG%"
    exit /b 1
)

echo.
echo DLL built OK: %BUILD_DIR%\wsf_shm.dll
