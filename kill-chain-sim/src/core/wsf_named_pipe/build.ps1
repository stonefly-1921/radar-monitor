// Build script for wsf_named_pipe.dll
// Uses MSVC via VS2022 BuildTools
// Simple Windows API DLL - no AFSIM SDK dependencies needed

$CC = "C:\\Program Files (x86)\\Microsoft Visual Studio\\2022\\BuildTools\\VC\\Tools\\MSVC\\14.44.35207\\bin\\Hostx64\\x64\\cl.exe"
$LINK = "C:\\Program Files (x86)\\Microsoft Visual Studio\\2022\\BuildTools\\VC\\Tools\\MSVC\\14.44.35207\\bin\\Hostx64\\x64\\link.exe"

$SrcDir = "D:\\afsim-2.9.0-win64\\swdev\\src\\wsf_plugins\\wsf_named_pipe"
$BuildDir = "D:\\afsim-2.9.0-win64\\swdev\\src\\wsf_plugins\\wsf_named_pipe\\build"
$OutputDir = "D:\\afsim-2.9.0-win64\\bin"

$cpp = "$SrcDir\\wsf_named_pipe.cpp"
$def = "$SrcDir\\wsf_named_pipe.def"
$obj = "$BuildDir\\wsf_named_pipe.obj"
$dll = "$OutputDir\\wsf_named_pipe.dll"

# Create build dir
if (!(Test-Path $BuildDir)) { New-Item -ItemType Directory -Path $BuildDir -Force | Out-Null }

Write-Host "=== Building wsf_named_pipe.dll ==="

# Compile
Write-Host "Compiling..."
& $CC /c /W3 /EHsc /MD /O2 /I. $cpp /Fo"$obj" /Fd"$BuildDir\wsf_named_pipe.pdb"
if ($LASTEXITCODE -ne 0) { Write-Host "COMPILATION FAILED"; exit 1 }
Write-Host "OK: wsf_named_pipe.obj"

# Link
Write-Host "Linking..."
& $LINK /DLL /OUT:"$dll" /DEF:"$def" /LIBPATH:"C:\Program Files (x86)\Windows Kits\10\Lib\10.0.26100.0\ucrt\x64" /LIBPATH:"C:\Program Files (x86)\Windows Kits\10\Lib\10.0.26100.0\um\x64" kernel32.lib user32.lib advapi32.lib "$obj"
if ($LASTEXITCODE -ne 0) { Write-Host "LINKING FAILED"; exit 1 }

Write-Host "=== SUCCESS: $dll ==="
Write-Host "Size: $((Get-Item $dll).Length) bytes"
