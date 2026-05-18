import struct
from src.core.dis.fire_control import FireControl
from src.core.dis.dis_protocol import EntityId, DisTimestamp

# Test our Fire PDU
fc = FireControl(exercise_id=1)
mission = fc.create_fire_mission(EntityId(25, 1, 1), EntityId(25, 1, 2), EntityId(25, 1, 1))
pdu = fc.build_fire_pdu_bytes(mission)

print('Our Fire PDU:')
print('  Length:', len(pdu), 'bytes')
print('  [0-3] Timestamp:', pdu[0:4].hex(), '=', struct.unpack('>I', pdu[0:4])[0])
print('  [4]     Version:', pdu[4])
print('  [5]     Exercise:', pdu[5])
print('  [6]     Type:', pdu[6], '(should be 2 for Fire)')
print('  [7]     Family:', pdu[7], '(should be 1 for Warfare)')
print('  [8-9]   Length:', pdu[8:10].hex(), '=', struct.unpack('>H', pdu[8:10])[0])
print('  [10-11] Padding:', pdu[10:12].hex())

# AFSIM's DIS timestamp format
print()
print('AFSIM DIS timestamp encoding:')
print('  frac_hour * 2147483647 << 1')
print('  T=10 seconds -> ', hex(int((10/3600.0) * 2147483647.0) << 1))

# Check what the actual timestamp is in our PDU
ts_value = struct.unpack('>I', pdu[0:4])[0]
print()
print('Our timestamp value:', ts_value)
if ts_value > 0:
    frac = ts_value >> 1
    seconds = (frac / 2147483647.0) * 3600
    print('  Decoded as seconds since hour:', seconds)
else:
    print('  This means 0 seconds')

# Check if AFSIM Entity State PDUs have different timestamp encoding
print()
print('Entity State PDU timestamp analysis:')
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.bind(('0.0.0.0', 3002))
sock.settimeout(2)

import time
start = time.time()
entity_pdu = None
while time.time() - start < 5:
    try:
        data, addr = sock.recvfrom(1500)
        if data[6] == 1 and len(data) == 144:  # Entity State
            entity_pdu = data
            break
    except:
        pass

sock.close()

if entity_pdu:
    print('Entity State PDU from', addr)
    print('  [0-3] Timestamp:', entity_pdu[0:4].hex(), '=', struct.unpack('>I', entity_pdu[0:4])[0])
    print('  [4] Version:', entity_pdu[4])
    print('  [5] Exercise:', entity_pdu[5])
    print('  [6] Type:', entity_pdu[6])
else:
    print('No Entity State PDU captured')