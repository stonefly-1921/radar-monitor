@echo off
set vcvars=C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvarsall.bat
call "%vcvars%" x64 >nul 2>&1
set CLM=C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Tools\MSVC\14.44.35207\bin\Hostx64\x64\cl.exe
set LINK="C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Tools\MSVC\14.44.35207\bin\Hostx64\x64\link.exe"
set SRC=d:\afsim-2.9.0-win64\swdev\src\wsf_plugins\wsf_named_pipe\wsf_named_pipe.cpp
set OBJ=d:\afsim-2.9.0-win64\swdev\src\wsf_plugins\wsf_named_pipe\temp_named_pipe.obj
set OUT=d:\afsim-2.9.0-win64\bin\wsf_named_pipe.dll
set LIBS=d:\afsim-2.9.0-win64\swdev\BUILD\lib\Release\wsf.lib d:\afsim-2.9.0-win64\swdev\BUILD\lib\Release\wsf_mil.lib d:\afsim-2.9.0-win64\swdev\BUILD\lib\Release\util.lib

echo === Compiling ===
"%CLM%" /c /nologo /EHsc /MD /I"d:\afsim-2.9.0-win64\swdev\src\core" /I"d:\afsim-2.9.0-win64\swdev\src\tools\util_script\source" /I"d:\afsim-2.9.0-win64\swdev\src\core\wsf_mil\source" "%SRC%" /Fo"%OBJ%" 2>&1
if errorlevel 1 goto :failed

echo === Linking ===
%LINK% /NOLOGO /DLL /OUT:"%OUT%" "%OBJ%" %LIBS% /LIBPATH:"d:\afsim-2.9.0-win64\swdev\BUILD\lib\Release" kernel32.lib user32.lib 2>&1
if errorlevel 1 goto :failed

echo === SUCCESS ===
copy /Y "%OUT%" "d:\afsim-2.9.0-win64\bin\wsf_named_pipe.dll.bak" >nul 2>&1
goto :end

:failed
echo === FAILED ===
exit /b 1

:end
