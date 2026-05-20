#!/bin/bash
# build_wsf_shm.sh - Build wsf_shm.dll with conda-forge GCC (MinGW target)
set -e

CC="D:/anaconda3/Library/bin/gcc.exe"
SRC_DIR="$(dirname "$0")"
DEST="D:/afsim-2.9.0-win64/bin/wsf_plugins"
SRC_FILE="$SRC_DIR/wsf_shm.c"

if [ ! -f "$SRC_FILE" ]; then
    echo "ERROR: Source not found: $SRC_FILE"
    exit 1
fi

mkdir -p "$DEST"

echo "Building wsf_shm.dll..."
$CC -shared -o "$DEST/wsf_shm.dll" "$SRC_FILE" \
    -DBUILD_DLL=1 \
    -O2 \
    -Wl,--out-implib,"$DEST/wsf_shm.lib" \
    2>&1

if [ -f "$DEST/wsf_shm.dll" ]; then
    SIZE=$(stat -c%s "$DEST/wsf_shm.dll" 2>/dev/null || stat -f%z "$DEST/wsf_shm.dll" 2>/dev/null)
    echo "SUCCESS: $DEST/wsf_shm.dll ($SIZE bytes)"
else
    echo "ERROR: Build failed"
    exit 1
fi
