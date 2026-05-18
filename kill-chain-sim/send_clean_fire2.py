import socket
import struct

# Create minimal Fire PDU - exactly what AFSIM expects
# AFSIM uses 4-byte timestamp (uint32) + 8 bytes of fields = 12 byte header
# Body: 84 bytes

# Body (84 bytes):
body = (
    b'\x00\x19\x00\x01\x00\x01' +  # 6: emitting_entity_id
    b'\x00\x19\x00\x01\x00\x02' +  # 6: target_entity_id
    b'\x00\x19\x00\x01\x00\x01' +  # 6: Munition_id
    b'\x00\x00\x00\x00\x00\x00' +  # 6: event_id
    b'\x00\x00\x00\x01' +          # 4: fire_mission_index
    b'\x00' * 24 +                  # 24: location (3 x double)
    b'\x00' * 8 +                   # 8: weapon_type
    b'\x00\x64\x00\x02' +          # 4: warhead, fuse
    b'\x00\x01\x00\x00' +          # 4: quantity, rate
    b'\x00' * 12 +                  # 12: velocity (3 x float)
    b'\x00' * 4                     # 4: range
)
print('Body length:', len(body), '(expected: 84)')

# Header (12 bytes): timestamp(4) + version(1) + exercise(1) + type(1) + family(1) + length(2) + padding(2)
total_len = 12 + len(body)  # 96 bytes

# Build header manually: 4 + 1 + 1 + 1 + 1 + 2 + 2 = 12 bytes
header = struct.pack('>I', 0)                      # timestamp (4 bytes)
header += struct.pack('>B', 6)                     # version
header += struct.pack('>B', 1)                     # exercise
header += struct.pack('>B', 2)                    # type (Fire)
header += struct.pack('>B', 1)                     # family (Warfare)
header += struct.pack('>H', total_len)            # length (2 bytes)
header += struct.pack('>H', 0)                     # padding (2 bytes)

pdu = header + body
print('Total PDU length:', len(pdu), '(expected: 96)')

# Verify header
print()
print('Header verification:')
print('  [0-3]   Timestamp:', pdu[0:4].hex(), '=', struct.unpack('>I', pdu[0:4])[0])
print('  [4]     Version:', pdu[4], '(should be 6)')
print('  [5]     Exercise:', pdu[5], '(should be 1)')
print('  [6]     Type:', pdu[6], '(should be 2)')
print('  [7]     Family:', pdu[7], '(should be 1)')
print('  [8-9]   Length:', pdu[8:10].hex(), '=', struct.unpack('>H', pdu[8:10])[0])
print('  [10-11] Padding:', pdu[10:12].hex())

# Send
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
sock.sendto(pdu, ('192.168.3.255', 3002))
sock.close()
print()
print('Sent to 192.168.3.255:3002')