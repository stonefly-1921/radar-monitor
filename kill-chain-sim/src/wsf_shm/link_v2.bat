@echo off
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvarsall.bat" x64
echo Linking wsf_shm_v2.dll...
link /DLL /OUT:"D:\afsim-2.9.0-win64\bin\wsf_plugins\wsf_shm_v2.dll" /MACHINE:X64 ^
  "D:\afsim-2.9.0-win64\bin\wsf_plugins\wsf_shm_v2.obj" ^
  kernel32.lib user32.lib
echo Link exit code: %ERRORLEVEL%
