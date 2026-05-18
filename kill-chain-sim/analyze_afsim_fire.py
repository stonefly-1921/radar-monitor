import socket
import struct

# Capture AFSIM Fire PDU
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.bind(('0.0.0.0', 3002))
sock.settimeout(5)

import time
afsim_fire = None
start = time.time()
while time.time() - start < 8:
    try:
        data, addr = sock.recvfrom(1500)
        if len(data) == 96 and data[6] == 2:
            afsim_fire = data
            break
    except:
        break

sock.close()

if not afsim_fire:
    print('No Fire PDU captured')
    exit()

print('AFSIM Fire PDU:')
print('Hex:', afsim_fire.hex())
print()
print('Field-by-field analysis:')
print('=' * 60)

# Header (12 bytes)
print('HEADER (12 bytes):')
print(f'  [0-3]   Timestamp: {afsim_fire[0:4].hex()} = {struct.unpack(">I", afsim_fire[0:4])[0]}')
print(f'  [4]     Version: {afsim_fire[4]} (should be 6)')
print(f'  [5]     Exercise: {afsim_fire[5]} (should be 1)')
print(f'  [6]     Type: {afsim_fire[6]} (should be 2 for Fire)')
print(f'  [7]     Family: {afsim_fire[7]} (should be 1)')
print(f'  [8-9]   Length: {afsim_fire[8:10].hex()} = {struct.unpack(">H", afsim_fire[8:10])[0]}')
print(f'  [10-11] Padding: {afsim_fire[10:12].hex()}')

# Body
body = afsim_fire[12:]
print()
print('BODY (84 bytes):')

offset = 0
print(f'  [12-17] Emitting Entity ID: {body[offset:offset+6].hex()}')
offset += 6

print(f'  [18-23] Target Entity ID: {body[offset:offset+6].hex()}')
offset += 6

print(f'  [24-29] Munition ID: {body[offset:offset+6].hex()}')
offset += 6

print(f'  [30-35] Event ID: {body[offset:offset+6].hex()}')
offset += 6

print(f'  [36-39] Fire Mission Index: {body[offset:offset+4].hex()} = {struct.unpack(">I", body[offset:offset+4])[0]}')
offset += 4

print(f'  [40-47] Location[0]: {body[offset:offset+8].hex()}')
offset += 8
print(f'  [48-55] Location[1]: {body[offset:offset+8].hex()}')
offset += 8
print(f'  [56-63] Location[2]: {body[offset:offset+8].hex()}')
offset += 8

print(f'  [64-71] Weapon Type: {body[offset:offset+8].hex()}')
offset += 8

print(f'  [72-73] Warhead: {body[offset:offset+2].hex()} = {struct.unpack(">H", body[offset:offset+2])[0]}')
offset += 2
print(f'  [74-75] Fuse: {body[offset:offset+2].hex()} = {struct.unpack(">H", body[offset:offset+2])[0]}')
offset += 2
print(f'  [76-77] Quantity: {body[offset:offset+2].hex()} = {struct.unpack(">H", body[offset:offset+2])[0]}')
offset += 2
print(f'  [78-79] Rate: {body[offset:offset+2].hex()} = {struct.unpack(">H", body[offset:offset+2])[0]}')
offset += 2

print(f'  [80-83] Velocity[0]: {body[offset:offset+4].hex()}')
offset += 4
print(f'  [84-87] Velocity[1]: {body[offset:offset+4].hex()}')
offset += 4
print(f'  [88-91] Velocity[2]: {body[offset:offset+4].hex()}')
offset += 4

print(f'  [92-95] Range: {body[offset:offset+4].hex()} = {struct.unpack(">f", body[offset:offset+4])[0]}')

print()
print(f'Total body offset: {offset} (should be 84)')