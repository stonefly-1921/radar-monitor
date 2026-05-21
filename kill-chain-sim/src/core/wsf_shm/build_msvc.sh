#!/bin/bash
# Build wsf_shm.dll using MSVC
set -e

AFSIM_SDK="/d/afsim-2.9.0-win64/swdev"
SRC_DIR="/c/Users/15041/.openclaw/workspace/kill-chain-sim/src/core/wsf_shm/source"
BUILD_DIR="/c/Users/15041/.openclaw/workspace/kill-chain-sim/src/core/wsf_shm/build"
VSCVARS="C:/Program Files (x86)/Microsoft Visual Studio/2022/BuildTools/VC/Auxiliary/Build/vcvars64.bat"
LOG="${BUILD_DIR}/build_msvc.log"

mkdir -p "$BUILD_DIR"
rm -f "$LOG"

# Build a temporary .bat file that does the actual compilation
cat > "${BUILD_DIR}/compile.bat" << 'BATEOF'
@echo off
setlocal

call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"

set CL=
set CL=!CL! /permissive- /EHsc /MD /O2 /W3 /c /nologo
set CL=!CL! /DWSF_STATIC_DEFINE /DUT_STATIC_DEFINE
set CL=!CL! /DWIN32 /D_WIN32 /D_WIN64 /DNDEBUG /D_MSC_VER=1916
set CL=!CL! /I"D:\afsim-2.9.0-win64\swdev\src\core\wsf\source"
set CL=!CL! /I"D:\afsim-2.9.0-win64\swdev\src\core\wsf\source\observer"
set CL=!CL! /I"D:\afsim-2.9.0-win64\swdev\src\core\wsf\source\comm"
set CL=!CL! /I"D:\afsim-2.9.0-win64\swdev\src\core\wsf_util\source"
set CL=!CL! /I"D:\afsim-2.9.0-win64\swdev\BUILD\wsf\source"
set CL=!CL! /I"D:\afsim-2.9.0-win64\swdev\BUILD\wsf\source\include"
set CL=!CL! /I"D:\afsim-2.9.0-win64\swdev\BUILD\util\source"
set CL=!CL! /I"D:\afsim-2.9.0-win64\swdev\src\tools\util\source"
set CL=!CL! /I"D:\afsim-2.9.0-win64\swdev\src\tools\util_script\source"
set CL=!CL! /I"D:\afsim-2.9.0-win64\swdev\BUILD"
set CL=!CL! /I"D:\afsim-2.9.0-win64\swdev\BUILD\build_wsf_fires"
set CL=!CL! /I"D:\afsim-2.9.0-win64\swdev\BUILD\util_script\source"
set CL=!CL! /I"D:\afsim-2.9.0-win64\swdev\BUILD\include"
set CL=!CL! /I"D:\afsim-2.9.0-win64\swdev\src\tools\dis\source"

echo Compiling: %~1
cl.exe %CL% /Fo"%~2" "%~1" >> "%~3" 2>&1
BATEOF

for src in wsf_plugin_entry WsfShmScenarioExtension WsfShmSimulationExtension; do
  SRC="${SRC_DIR}/${src}.cpp"
  if [ ! -f "$SRC" ]; then
    echo "SKIP (not found): $src"
    continue
  fi
  OBJ="${BUILD_DIR}/${src}.obj"
  echo "=== Compiling: $src ==="

  cmd.exe /c "$(printf 'call ^"%%1^" ^"%%2^" ^"%%3^" ^"%%4^" ^"%%5^"' \
    "$(cygpath -w "${BUILD_DIR}/compile.bat")" \
    "$(cygpath -w "$SRC")" \
    "$(cygpath -w "$OBJ")" \
    "$(cygpath -w "$LOG")")" || {
    echo "FAILED: $src"
    cat "$LOG"
    exit 1
  }

  if grep -qi "error\|failed" "$LOG" 2>/dev/null; then
    echo "FAILED: $src (check log)"
    tail -20 "$LOG"
    exit 1
  fi
  echo "OK: $src"
done

echo ""
echo "=== Linking DLL ==="
DLL="${BUILD_DIR}/wsf_shm.dll"

cat > "${BUILD_DIR}/link.bat" << 'BATEOF'
@echo off
setlocal
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
link /DLL /OUT:"%~1" "%~2" "%~3" "%~4" /LIBPATH:"D:\afsim-2.9.0-win64\swdev\BUILD\lib" ws2_32.lib psapi.lib /IGNORE:4217 /IGNORE:4199 >> "%~5" 2>&1
BATEOF

cmd.exe /c "$(printf 'call ^"%%1^" ^"%%2^" ^"%%3^" ^"%%4^" ^"%%5^" ^"%%6^"' \
  "$(cygpath -w "${BUILD_DIR}/link.bat")" \
  "$(cygpath -w "$DLL")" \
  "$(cygpath -w "${BUILD_DIR}/wsf_plugin_entry.obj")" \
  "$(cygpath -w "${BUILD_DIR}/WsfShmScenarioExtension.obj")" \
  "$(cygpath -w "${BUILD_DIR}/WsfShmSimulationExtension.obj")" \
  "$(cygpath -w "$LOG")")" || {
  echo "LINK FAILED"
  tail -30 "$LOG"
  exit 1
}

echo "DLL built: $DLL"
ls -la "$DLL"
echo ""
echo "Verifying exports:"
dumpbin /EXPORTS "$DLL" 2>/dev/null | grep -E "WSF_|wsf_" || true
