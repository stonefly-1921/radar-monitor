# Try to extract database key from WeChat process memory using pymem
import psutil
import pymem
import struct

# Find WeChat process
wechat_pid = None
for p in psutil.process_iter():
    if p.name() == 'WeChat.exe':
        wechat_pid = p.pid
        print(f"Found WeChat.exe with PID: {wechat_pid}")
        break

if not wechat_pid:
    print("WeChat.exe not found!")
    exit(1)

# Open process with pymem
pm = pymem.Pymem()
pm.open_process_from_id(wechat_pid)

# Get module base address for WeChatWin.dll
wechatwin_addr = pymem.process.module_from_name(pm.process_handle, "WeChatWin.dll")
print(f"WeChatWin.dll base: {hex(wechatwin_addr)}")

# Try to find database key using known patterns
# The key is typically stored in memory near specific WeChat executable strings
# Let's scan for common key-related patterns
import ctypes

PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010

# Scan memory regions for potential key material
key_patterns = [
    b'key=', b'db_key=', b'password=', b'passwd=',
    b'MicroMsg.db', b'ChatMsg.db', b'FFDB'
]

addresses_found = {}
for proc in psutil.process_iter():
    if proc.name() == 'WeChat.exe':
        try:
            for mem_map in proc.memory_maps():
                pass  # just to have access
        except:
            pass

print("\nAttempting memory search for database key...")
# Use pymem's memory search functionality
try:
    # Search for SQLite database header in memory
    # Encrypted DBs won't have this, but unencrypted sections might
    # The actual key is usually in a specific memory range
    client_addr = pymem.process.module_from_name(pm.process_handle, "WeChatWin.dll")
    
    # Read a chunk of memory from the module
    module_size = 0x1000000  # 16MB
    data = pymem.memory.read_memory(pm.process_handle, client_addr, module_size)
    
    # Look for common patterns
    for pattern in [b'COMINFOTABLE', b'KEYID', b'dbkey']:
        offset = data.find(pattern)
        if offset != -1:
            print(f"Found pattern {pattern} at offset {hex(offset)}")
            # Read around that area
            context = pymem.memory.read_memory(pm.process_handle, client_addr + offset - 32, 128)
            print(f"Context: {context[:64].hex()}")
except Exception as e:
    print(f"Error: {e}")

pm.close_process()
