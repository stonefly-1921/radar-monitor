#!/bin/bash
# build_wsf_shm_plugin.sh
# Build wsf_shm.dll with correct WSF_PluginVersion entry point
# Uses MinGW-w64 GCC 16.1.0

set -e

CXX="/c/Users/15041/mингw64/mingw64/bin/g++.exe"
STRIP="/c/Users/15041/mингw64/mingw64/bin/strip.exe"

SRC_DIR="/c/Users/15041/.openclaw/workspace/kill-chain-sim/src/core/wsf_shm/source"
BUILD_DIR="/c/Users/15041/.openclaw/workspace/kill-chain-sim/src/core/wsf_shm/build"
AFSIM_SDK="/d/afsim-2.9.0-win64/swdev"

# Include paths (order matters)
INCLUDES="
  -I${AFSIM_SDK}/src/core/wsf/source
  -I${AFSIM_SDK}/src/core/wsf/source/observer
  -I${AFSIM_SDK}/src/core/wsf_util/source
  -I${AFSIM_SDK}/src/core/wsf/source/comm
  -I${AFSIM_SDK}/BUILD/wsf/source
  -I${AFSIM_SDK}/BUILD/wsf/source/include
  -I${AFSIM_SDK}/BUILD/util/source
  -I${AFSIM_SDK}/src/tools/util/source
  -I${AFSIM_SDK}/src/tools/util_script/source
  -I${AFSIM_SDK}/BUILD
  -I${AFSIM_SDK}/BUILD/build_wsf_fires
  -I${AFSIM_SDK}/BUILD/util_script/source
  -I${AFSIM_SDK}/BUILD/include
"

# Defines
DEFS="
  -DWSF_STATIC_DEFINE
  -DUT_STATIC_DEFINE
  -D_MSC_VER=1916
  -DWIN32
  -D_WIN32
  -D_WIN64
  -D__MINGW32__
  -D__MINGW64__
  -DNDEBUG
"

# Flags
CXXFLAGS="-std=c++17 -O2 -Wall -Wno-unused-parameter -Wno-deprecated-declarations -fpermissive -shared"

mkdir -p "$BUILD_DIR"

OBJECTS=""

for src in wsf_plugin_entry WsfShmScenarioExtension WsfShmComponent; do
  SRC="${SRC_DIR}/${src}.cpp"
  if [ -f "$SRC" ]; then
    echo "Compiling: $src"
    OBJ="${BUILD_DIR}/${src}.o"
    $CXX -c $CXXFLAGS $DEFS $INCLUDES -o "$OBJ" "$SRC" 2>&1 || {
      echo "FAILED: $src"
      exit 1
    }
    OBJECTS="$OBJECTS $OBJ"
  fi
done

echo "Linking DLL..."
DLL="${BUILD_DIR}/wsf_shm.dll"
$CXX $CXXFLAGS $DEFS $INCLUDES $OBJECTS \
  -o "$DLL" \
  -lws2_32 -lpsapi \
  -Wl,--enable-auto-import \
  -Wl,--out-implib,"${BUILD_DIR}/libwsf_shm.a" 2>&1

echo "Stripping symbols..."
$STRIP --strip-all "$DLL" 2>/dev/null || true

echo ""
echo "DLL built: $DLL"
ls -la "$DLL"

echo ""
echo "Verifying exports:"
dumpbin /EXPORTS "$DLL" 2>/dev/null | grep -E "WSF_|wsf_" || true
objdump -p "$DLL" 2>/dev/null | grep -A 20 "Export Table" | head -25 || true
