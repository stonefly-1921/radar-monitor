@echo off
REM build_wsf_shm_msvc.bat - Build wsf_shm.dll with MSVC 2022
REM Must be run from VS2022 Developer Command Prompt or after calling vcvarsall.bat

set SRC_DIR=..\wsf_shm
set OUT_DIR=..\..\..\..\..\..\..\..\d:\afsim-2.9.0-win64\bin\wsf_plugins
set CL_DIR=C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Tools\MSVC\14.44.35207
set SDK_DIR=C:\Program Files (x86)\Windows Kits\10
set LIB_DIR=D:\afsim-2.9.0-win64\bin\lib

set CFLAGS=/EHsc /MT /W3 /O2 /DNDEBUG /D_MBCS /DWIN32_LEAN_AND_MEAN /DWSF_SHM_EXPORTS
set LFLAGS=/DLL /NODEFAULTLIB:libcmt.lib /OUT:%OUT_DIR%\wsf_shm.dll kernel32.lib user32.lib

REM C-only compile (no AFSIM SDK headers needed)
%CL_DIR%\bin\Hostx64\x64\cl.exe %CFLAGS% ^
  %SRC_DIR%\wsf_shm.c ^
  /Fe:%OUT_DIR%\wsf_shm.dll ^
  /link %LFLAGS%

echo.
echo === Build complete: %OUT_DIR%\wsf_shm.dll ===
dir %OUT_DIR%\wsf_shm.dll
