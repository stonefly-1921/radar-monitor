import socket
import struct

print('Capturing PDUs from AFSIM...')
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.bind(('0.0.0.0', 3002))
sock.settimeout(5)

pdus = []
import time
start = time.time()
while time.time() - start < 8:
    try:
        data, addr = sock.recvfrom(1500)
        if len(data) >= 12:
            pdus.append((data, addr, len(data)))
    except:
        break

sock.close()

print(f'Captured {len(pdus)} PDUs')
print()

# Analyze Entity State PDUs (type=1, 144 bytes)
for data, addr, length in pdus:
    if length == 144 and data[6] == 1:
        print(f'Entity State PDU from {addr}:')
        print(f'  Length: {len(data)} bytes')
        print()
        print('Header (first 16 bytes):')
        for i in range(min(16, len(data))):
            print(f'  [{i:2d}] {data[i]:3d} (0x{data[i]:02x})')
        print()
        print('Header hex:', data[:16].hex())
        print()
        
        # Try different timestamp interpretations
        print('Timestamp interpretations:')
        ts_bytes = data[0:4]
        ts_val = struct.unpack('>I', ts_bytes)[0]
        print(f'  As uint32 (big-endian): {ts_val}')
        
        # If it's DIS timestamp with bit shift
        frac = ts_val >> 1
        seconds = (frac / 2147483647.0) * 3600
        print(f'  As DIS timestamp (frac_hour * 2^31-1 << 1): {seconds:.3f} seconds in hour')
        
        print()
        print('Entity ID (bytes 12-17):', data[12:18].hex())
        print('Entity Type (bytes 18-25):', data[18:26].hex())
        break