@echo off
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvarsall.bat" x64

set SDK=D:\afsim-2.9.0-win64\swdev
set SRC=%SDK%\src\wsf_plugins\wsf_shm\source
set OUT=D:\afsim-2.9.0-win64\bin\wsf_plugins
set LIB=%SDK%\BUILD

echo === Compiling wsf_shm with full SDK includes + ws f_export.h ===
echo.

rem Core includes (must have wsf_export.h AND WsfSimulation.hpp)
set INCLUDES=/I"%SRC%" ^
  /I"%SDK%\src\core\wsf\source" ^
  /I"%SDK%\src\core\wsf\source\comm" ^
  /I"%SDK%\src\core\wsf\source\event_pipe" ^
  /I"%SDK%\src\core\wsf\source\mover" ^
  /I"%SDK%\src\core\wsf\source\observer" ^
  /I"%SDK%\src\core\wsf\source\processor" ^
  /I"%SDK%\src\core\wsf\source\sensor" ^
  /I"%SDK%\BUILD\wsf\source\include" ^
  /I"%SDK%\BUILD\wsf\source" ^
  /I"%SDK%\BUILD\include" ^
  /I"%SDK%\src\tools\util\source" ^
  /I"%SDK%\BUILD\util\source" ^
  /I"%SDK%\src\tools\util_script\source" ^
  /I"%SDK%\BUILD\util_script\source" ^
  /I"%SDK%\src\tools\geodata\source" ^
  /I"%SDK%\BUILD\geodata\source" ^
  /I"%SDK%\src\tools\genio\source" ^
  /I"%SDK%\BUILD\genio\source" ^
  /I"%SDK%\src\tools\packetio\source" ^
  /I"%SDK%\BUILD\packetio\source" ^
  /I"%SDK%\src\tools\dis\source" ^
  /I"%SDK%\BUILD\dis\source" ^
  /I"%SDK%\src\tools\tracking_filters\source" ^
  /I"%SDK%\BUILD\tracking_filters\source" ^
  /I"%SDK%\src\tools\profiling\source" ^
  /I"%SDK%\BUILD\profiling\source\.." ^
  /I"%SDK%\src\core\wsf_util\source" ^
  /I"%SDK%\src\core\wsf_mil\source" ^
  /I"%SDK%\BUILD\build_wsf_mil\source" ^
  /I"%SDK%\src\wsf_plugins\wsf_p6dof\source" ^
  /I"%SDK%\BUILD\build_wsf_p6dof\source" ^
  /I"%SDK%\src\wsf_plugins\wsf_p6dof\p6dof\source" ^
  /I"%SDK%\BUILD\build_wsf_p6dof\p6dof\source" ^
  /I"%SDK%\src\wsf_plugins\wsf_six_dof\source" ^
  /I"%SDK%\BUILD\build_wsf_six_dof\source" ^
  /I"%SDK%\src\wsf_plugins\wsf_brawler\source" ^
  /I"%SDK%\BUILD\build_wsf_brawler\source" ^
  /I"%SDK%\src\wsf_plugins\wsf_brawler\brawler\source" ^
  /I"%SDK%\BUILD\build_wsf_brawler\brawler\source"

rem Preprocessor definitions (critical for dllexport/dllimport)
set DEFS=/DWIN32 /D_WINDOWS /DNDEBUG /D_MBCS /DWIN32_LEAN_AND_MEAN /DNOMINMAX /DPROMOTE_HARDWARE_EXCEPTIONS /DSWDEV_ALL_USE_DLL /Dwsf_shm_EXPORTS /D_CRT_SECURE_NO_WARNINGS /D_SCL_SECURE_NO_WARNINGS /D_CRT_NONSTDC_NO_WARNINGS /D_SILENCE_TR1_NAMESPACE_DEPRECATION_WARNING

set FLAGS=/EHsc /MT /W3 /O2 /utf-8 /wd4251

echo Compiling WsfShmScenarioExtension.cpp...
cl %FLAGS% %DEFS% %INCLUDES% /c "%SRC%\WsfShmScenarioExtension.cpp" /Fo"%OUT%\WsfShmScenarioExtension.obj" 2>&1
echo.

echo Compiling WsfShmSimulationExtension.cpp...
cl %FLAGS% %DEFS% %INCLUDES% /c "%SRC%\WsfShmSimulationExtension.cpp" /Fo"%OUT%\WsfShmSimulationExtension.obj" 2>&1
echo.

echo Compiling WsfShmComponent.cpp...
cl %FLAGS% %DEFS% %INCLUDES% /c "%SRC%\WsfShmComponent.cpp" /Fo"%OUT%\WsfShmComponent.obj" 2>&1
echo.

echo === Linking wsf_shm_v2.dll ===
if errorlevel 1 goto :done

link /DLL /OUT:"%OUT%\wsf_shm_v2.dll" /MACHINE:X64 ^
  "%OUT%\WsfShmScenarioExtension.obj" ^
  "%OUT%\WsfShmSimulationExtension.obj" ^
  "%OUT%\WsfShmComponent.obj" ^
  "%LIB%\wsf.lib" ^
  "%LIB%\wsf_air_combat.lib" ^
  "%LIB%\wsf_util.lib" ^
  "%LIB%\wsf_mil.lib" ^
  "%LIB%\util.lib" ^
  "%LIB%\util_script.lib" ^
  "%LIB%\tracking_filters.lib" ^
  "%LIB%\genio.lib" ^
  "%LIB%\packetio.lib" ^
  "%LIB%\dis.lib" ^
  "%LIB%\profiling.lib" ^
  kernel32.lib user32.lib gdi32.lib winspool.lib shell32.lib ole32.lib oleaut32.lib uuid.lib comdlg32.lib advapi32.lib 2>&1

:done
echo Build done. Check above for errors.
