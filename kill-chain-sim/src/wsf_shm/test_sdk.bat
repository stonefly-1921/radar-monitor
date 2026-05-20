@echo off
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvarsall.bat" x64

set SDK=D:\afsim-2.9.0-win64\swdev
set SRC=%SDK%\src\wsf_plugins\wsf_shm\source
set OUT=D:\afsim-2.9.0-win64\bin\wsf_plugins

rem Full SDK include paths
set INCLUDES=/I"%SRC%" /I"%SDK%\src\core\wsf\source" /I"%SDK%\src\core\wsf\source\comm" /I"%SDK%\src\core\wsf\source\event_pipe" /I"%SDK%\src\core\wsf\source\mover" /I"%SDK%\src\core\wsf\source\observer" /I"%SDK%\src\core\wsf\source\processor" /I"%SDK%\src\core\wsf\source\sensor" /I"%SDK%\BUILD\wsf\source\include" /I"%SDK%\BUILD\wsf\source" /I"%SDK%\BUILD" /I"%SDK%\BUILD\include" /I"%SDK%\src\tools\util\source" /I"%SDK%\BUILD\util\source" /I"%SDK%\src\tools\util_script\source" /I"%SDK%\BUILD\util_script" /I"%SDK%\BUILD\util_script\source" /I"%SDK%\src\tools\geodata\source" /I"%SDK%\BUILD\geodata\source" /I"%SDK%\src\tools\genio\source" /I"%SDK%\BUILD\genio" /I"%SDK%\src\tools\packetio\source" /I"%SDK%\BUILD\packetio" /I"%SDK%\src\tools\dis\source" /I"%SDK%\BUILD\dis" /I"%SDK%\src\tools\tracking_filters\source" /I"%SDK%\BUILD\tracking_filters" /I"%SDK%\src\tools\profiling\source" /I"%SDK%\BUILD\profiling\source" /I"%SDK%\src\core\wsf_util\source" /I"%SDK%\src\core\wsf_mil\source" /I"%SDK%\BUILD\build_wsf_mil\source" /I"%SDK%\src\wsf_plugins\wsf_p6dof\source" /I"%SDK%\BUILD\build_wsf_p6dof" /I"%SDK%\src\wsf_plugins\wsf_p6dof\p6dof\source" /I"%SDK%\BUILD\build_wsf_p6dof\p6dof" /I"%SDK%\src\wsf_plugins\wsf_six_dof\source" /I"%SDK%\BUILD\build_wsf_six_dof" /I"%SDK%\src\wsf_plugins\wsf_brawler\source" /I"%SDK%\BUILD\build_wsf_brawler" /I"%SDK%\src\wsf_plugins\wsf_brawler\brawler\source" /I"%SDK%\BUILD\build_wsf_brawler\brawler"

rem CRITICAL: Both wsf_EXPORTS AND UT_PLUGIN_EXPORTS needed for dllexport
rem Also add UT_STATIC_DEFINE to avoid ut_export.h dllimport
set DEFS=/DWIN32 /D_WINDOWS /DNDEBUG /D_MBCS /DWIN32_LEAN_AND_MEAN /DNOMINMAX /DPROMOTE_HARDWARE_EXCEPTIONS /DSWDEV_ALL_USE_DLL /Dwsf_shm_EXPORTS /DUT_PLUGIN_EXPORTS /DUT_STATIC_DEFINE /D_CRT_SECURE_NO_WARNINGS /D_SCL_SECURE_NO_WARNINGS /D_CRT_NONSTDC_NO_WARNINGS /D_SILENCE_TR1_NAMESPACE_DEPRECATION_WARNING

echo Compiling WsfShmScenarioExtension.cpp with both wsf_EXPORTS and UT_PLUGIN_EXPORTS...
cl /EHsc /MT /W3 /O2 /utf-8 /wd4251 %DEFS% %INCLUDES% /c "%SRC%\WsfShmScenarioExtension.cpp" /Fo"%OUT%\test_scenario.obj" 2>&1
echo Exit: %ERRORLEVEL%
