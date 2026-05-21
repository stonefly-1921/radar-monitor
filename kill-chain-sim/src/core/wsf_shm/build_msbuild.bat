@echo off
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"

set MSBUILD="C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\MSBuild\Current\Bin\MSBuild.exe"

REM Skip ZERO_CHECK and SDK version check
%MSBUILD% "D:\afsim-2.9.0-win64\swdev\BUILD\build_wsf_shm\wsf_shm.vcxproj" /p:Configuration=Release /p:Platform=x64 /v:minimal /p:WindowsTargetPlatformVersionOverride=10.0.26100.0 /p:SkipInvalidConfigurations=true
