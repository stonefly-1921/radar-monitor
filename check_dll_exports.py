import ctypes
from ctypes import wintypes

kernel32 = ctypes.windll.kernel32

dll = kernel32.LoadLibraryExW(r'D:\afsim-2.9.0-win64\bin\wsf_shm.dll', None, 0)
if not dll:
    print(f'Load failed: {kernel32.GetLastError()}')
    exit()

print(f'DLL handle: {dll}')

# Try ordinals 1-200
found = []
for ordinal in range(1, 200):
    addr = kernel32.GetProcAddress(dll, ctypes.c_void_p(ordinal))
    if addr:
        found.append((ordinal, hex(addr)))

print(f'Total exports: {len(found)}')
for ordinal, addr in found[:50]:
    print(f'  Ordinal {ordinal}: {addr}')

if len(found) > 50:
    print(f'  ... and {len(found)-50} more')

# Also try by name for a few common patterns
names_to_try = [
    b'DllMain',
    b'wsf_shm',
    b'WsfShmExtension',
    b'GetExtensionName',
    b'PluginMain',
    b'DllGetClassObject',
]

print('\nBy name:')
for name in names_to_try:
    addr = kernel32.GetProcAddress(dll, name)
    if addr:
        print(f'  {name.decode()}: {hex(addr)}')
    else:
        print(f'  {name.decode()}: NOT FOUND')

kernel32.FreeLibrary(dll)