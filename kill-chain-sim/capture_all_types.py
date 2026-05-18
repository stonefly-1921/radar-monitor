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

for data, addr, length in pdus:
    pdu_type = data[6]
    print(f'{addr}: type={pdu_type} len={length}')

print()

# Look at Entity State PDU format
for data, addr, length in pdus:
    if length == 144 and data[6] == 1:
        print('Entity State PDU:')
        print(f'  Full hex: {data.hex()}')
        print()
        print('Header bytes 0-11:')
        for i in range(12):
            print(f'  [{i:2d}] {data[i]:3d} (0x{data[i]:02x})')
        break