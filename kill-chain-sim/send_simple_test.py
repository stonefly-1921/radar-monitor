import socket
import struct

# Create a minimal Fire PDU based on AFSIM source
# Header: timestamp(4) + version(1) + exercise(1) + type(1) + family(1) + length(2) + padding(2) = 12 bytes
# Body: 84 bytes (from DisFire::GetMemberData)

# Body parts (in order from AFSIM source):
# mFiringEntity (6 bytes)
# mTargetEntity (6 bytes)  
# mWeaponEntity (6 bytes)
# mEvent (6 bytes)
# mFireMissionIndex (4 bytes)
# mLocation (24 bytes = 3 x double)
# mWeaponType (8 bytes)
# mWarhead (2 bytes)
# mFuse (2 bytes)
# mQuantity (2 bytes)
# mRate (2 bytes)
# mVelocity (12 bytes = 3 x float)
# mRange (4 bytes)
# Total body: 6+6+6+6+4+24+8+2+2+2+2+12+4 = 84 bytes

body = (
    b'\x00\x19\x00\x01\x00\x01' +  # firing entity: site=25, app=1, entity=1
    b'\x00\x19\x00\x01\x00\x02' +  # target entity: site=25, app=1, entity=2
    b'\x00\x19\x00\x01\x00\x01' +  # weapon entity (Munition): same
    b'\x00\x00\x00\x00\x00\x00' +  # event id: all zeros
    b'\x00\x00\x00\x01' +          # fire mission index: 1
    b'\x00' * 24 +                  # location: 0,0,0
    b'\x00' * 8 +                   # weapon type: zeros
    b'\x00\x64' +                   # warhead: 100
    b'\x00\x02' +                   # fuse: 2
    b'\x00\x01' +                   # quantity: 1
    b'\x00\x00' +                   # rate: 0
    b'\x00' * 12 +                  # velocity: 0,0,0
    b'\x00\x00\x00\x00'            # range: 0
)

print('Body length:', len(body), '(should be 84)')

# Header
total_len = 12 + len(body)  # 96 bytes
timestamp = struct.pack('>I', 0)  # 0 seconds
header = timestamp + struct.pack('>BBBBHH', 6, 1, 2, 1, total_len, 0)

pdu = header + body

print('Total PDU:', len(pdu), 'bytes (should be 96)')
print('Header:')
print('  [0-3]   Timestamp:', pdu[0:4].hex())
print('  [4]     Version:', pdu[4])
print('  [5]     Exercise:', pdu[5])
print('  [6]     Type:', pdu[6], '(Fire=2)')
print('  [7]     Family:', pdu[7], '(Warfare=1)')
print('  [8-9]   Length:', pdu[8:10].hex(), '=', struct.unpack('>H', pdu[8:10])[0])
print('  [10-11] Padding:', pdu[10:12].hex())
print()
print('Sending...')

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
sock.sendto(pdu, ('192.168.3.255', 3002))
sock.close()
print('Done')