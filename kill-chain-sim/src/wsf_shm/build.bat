@echo off
setlocal
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvarsall.bat" x64

cl /EHsc /MT /W3 /O2 /DNDEBUG /D_MBCS /DWIN32_LEAN_AND_MEAN /utf-8 ^
  "C:\Users\15041\.openclaw\workspace\kill-chain-sim\src\wsf_shm\wsf_shm.c" ^
  /Fe:"D:\afsim-2.9.0-win64\bin\wsf_plugins\wsf_shm.dll" ^
  /link /DLL kernel32.lib user32.lib

echo.
if exist "D:\afsim-2.9.0-win64\bin\wsf_plugins\wsf_shm.dll" (
    echo SUCCESS
    dir "D:\afsim-2.9.0-win64\bin\wsf_plugins\wsf_shm.dll"
) else (
    echo FAILED
)
