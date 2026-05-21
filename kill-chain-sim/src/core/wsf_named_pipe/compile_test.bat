@echo off
set vcvars=C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvarsall.bat
call "%vcvars%" x64 >nul 2>&1
set CLM=C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Tools\MSVC\14.44.35207\bin\Hostx64\x64\cl.exe
set SRC=d:\afsim-2.9.0-win64\swdev\src\wsf_plugins\wsf_named_pipe\wsf_named_pipe.cpp
set OBJ=d:\afsim-2.9.0-win64\swdev\src\wsf_plugins\wsf_named_pipe\temp_named_pipe.obj
set AFSIM_SDK=d:\afsim-2.9.0-win64\swdev\src\core
set UT_SDK=d:\afsim-2.9.0-win64\swdev\src\tools\util_script\source
set UT_SDK2=d:\afsim-2.9.0-win64\swdev\src\tools\util\source
"%CLM%" /c /nologo /EHsc /MD /I"%AFSIM_SDK%" /I"%UT_SDK%" /I"%UT_SDK2%" /I"d:\afsim-2.9.0-win64\swdev\src\core\wsf_mil\source" "%SRC%" /Fo"%OBJ%" 2>&1
