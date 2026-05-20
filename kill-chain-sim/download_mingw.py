#!/usr/bin/env python3
"""Download MinGW-w64 from repo.msys2.org and extract to C:/temp/mingw64"""
import urllib.request
import zstandard as zstd
import tarfile
import os
import sys

# Packages needed for MinGW-w64 gcc
PACKAGES = [
    # Core
    ("https://repo.msys2.org/mingw/x86_64/mingw-w64-x86_64-headers-14.0.0-2-any.pkg.tar.zst", "mingw64/mingw64/include"),
    ("https://repo.msys2.org/mingw/x86_64/mingw-w64-x86_64-crt-14.0.0-2-any.pkg.tar.zst", "mingw64/"),
    ("https://repo.msys2.org/mingw/x86_64/mingw-w64-x86_64-runtime-14.0.0-2-any.pkg.tar.zst", "mingw64/"),
    ("https://repo.msys2.org/mingw/x86_64/mingw-w64-x86_64-libwinpthread-14.0.0-2-any.pkg.tar.zst", "mingw64/"),
    ("https://repo.msys2.org/mingw/x86_64/mingw-w64-x86_64-winpthreads-14.0.0-2-any.pkg.tar.zst", "mingw64/"),
    # Libraries
    ("https://repo.msys2.org/mingw/x86_64/mingw-w64-x86_64-libzstd-1.5.5-1-x86_64.pkg.tar.zst", "mingw64/"),
    ("https://repo.msys2.org/mingw/x86_64/mingw-w64-x86_64-zlib-1.3.1-1-x86_64.pkg.tar.zst", "mingw64/"),
    ("https://repo.msys2.org/mingw/x86_64/mingw-w64-x86_64-libzlib-1.3.1-1-x86_64.pkg.tar.zst", "mingw64/"),
    ("https://repo.msys2.org/mingw/x86_64/mingw-w64-x86_64-gcc-libs-14.2.0-3-any.pkg.tar.zst", "mingw64/"),
    # Toolchain
    ("https://repo.msys2.org/mingw/x86_64/mingw-w64-x86_64-binutils-2.41-4-x86_64.pkg.tar.zst", "mingw64/"),
    ("https://repo.msys2.org/mingw/x86_64/mingw-w64-x86_64-make-4.4.1-2-x86_64.pkg.tar.zst", "mingw64/"),
    ("https://repo.msys2.org/mingw/x86_64/mingw-w64-x86_64-gcc-14.2.0-3-any.pkg.tar.zst", "mingw64/"),
]

DEST = "C:/temp/mingw64"
os.makedirs(DEST, exist_ok=True)
os.makedirs("C:/temp/pkgs", exist_ok=True)


def extract_zst_tar(pkg_url, extract_to):
    """Download a .pkg.tar.zst and extract it."""
    filename = pkg_url.split("/")[-1]
    pkg_path = f"C:/temp/pkgs/{filename}"

    if os.path.exists(pkg_path):
        print(f"  Already downloaded: {filename}")
    else:
        print(f"  Downloading {filename}...")
        urllib.request.urlretrieve(pkg_url, pkg_path)

    print(f"  Extracting {filename}...")
    try:
        with open(pkg_path, 'rb') as f:
            dctx = zstd.ZstdDecompressor()
            with dctx.stream_reader(f) as dr:
                with tarfile.open(fileobj=dr, mode='r') as t:
                    t.extractall(extract_to)
        print(f"  Done: {filename}")
        return True
    except Exception as e:
        print(f"  FAILED: {e}")
        return False


if __name__ == "__main__":
    for url, extract_subdir in PACKAGES:
        extract_path = os.path.join(DEST, extract_subdir)
        print(f"\nProcessing: {url.split('/')[-1]}")
        ok = extract_zst_tar(url, extract_path)
        if not ok:
            print("STOPPING due to extraction error")
            sys.exit(1)

    print(f"\n\n=== DONE ===")
    print(f"MinGW-w64 installed at: {DEST}")
    print(f"Add to PATH: {DEST}/mingw64/bin")
