@echo off
REM build_wsf_named_pipe.bat - Build wsf_named_pipe.dll
REM Requires: VS2022 BuildTools + Windows SDK 10.0.26100.0
REM
REM Usage: Double-click this file, or: cmd /c build.bat

set VSCMD=C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Tools\MSVC\14.44.35207\bin\Hostx64\x64
set CC=%VSCMD%\cl.exe
set LINK=%VSCMD%\link.exe
set MSVC_INC=C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Tools\MSVC\14.44.35207\include
set WINSDK_INC=C:\Program Files (x86)\Windows Kits\10\Include\10.0.26100.0
set MSVC_LIB=C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Tools\MSVC\14.44.35207\lib\x64
set WINSDK_LIB=C:\Program Files (x86)\Windows Kits\10\Lib\10.0.26100.0

set SRC=D:\afsim-2.9.0-win64\swdev\src\wsf_plugins\wsf_named_pipe\wsf_named_pipe.cpp
set DEF=D:\afsim-2.9.0-win64\swdev\src\wsf_plugins\wsf_named_pipe\wsf_named_pipe.def
set OBJ=D:\afsim-2.9.0-win64\swdev\src\wsf_plugins\wsf_named_pipe\build\wsf_named_pipe.obj
set DLL=D:\afsim-2.9.0-win64\bin\wsf_named_pipe.dll

echo === Building wsf_named_pipe.dll ===
if not exist "D:\afsim-2.9.0-win64\swdev\src\wsf_plugins\wsf_named_pipe\build" mkdir "D:\afsim-2.9.0-win64\swdev\src\wsf_plugins\wsf_named_pipe\build"

echo === Compile ===
%CC% /c /W3 /EHsc /MD /O2 /I"%MSVC_INC%" /I"%WINSDK_INC%\ucrt" /I"%WINSDK_INC%\shared" /I"%WINSDK_INC%\um" /Fo"%OBJ%" "%SRC%"
if errorlevel 1 goto :fail

echo === Link ===
%LINK% /DLL /OUT:"%DLL%" /DEF:"%DEF%" /LIBPATH:"%MSVC_LIB%" /LIBPATH:"%WINSDK_LIB%\um\x64" /LIBPATH:"%WINSDK_LIB%\ucrt\x64" msvcprt.lib kernel32.lib user32.lib advapi32.lib "%OBJ%"
if errorlevel 1 goto :fail

echo.
echo SUCCESS: %DLL%
dir "%DLL%"
goto :eof

:fail
echo.
echo FAILED
exit /b 1
