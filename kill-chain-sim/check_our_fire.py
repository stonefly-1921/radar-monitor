import struct
from src.core.dis.fire_control import FireControl
from src.core.dis.dis_protocol import EntityId

fc = FireControl(exercise_id=1)
mission = fc.create_fire_mission(
    launcher_id=EntityId(25, 1, 1),
    target_id=EntityId(25, 1, 2),
    Munition_id=EntityId(25, 1, 1)
)
pdu = fc.build_fire_pdu_bytes(mission)

print('Our Fire PDU breakdown:')
print('=' * 60)
print(f'[0-3]   Timestamp: {pdu[0:4].hex()} = {struct.unpack(">I", pdu[0:4])[0]}')
print(f'[4]     Version: {pdu[4]}')
print(f'[5]     Exercise: {pdu[5]}')
print(f'[6]     Type: {pdu[6]}')
print(f'[7]     Family: {pdu[7]}')
print(f'[8-9]   Length: {pdu[8:10].hex()} = {struct.unpack(">H", pdu[8:10])[0]}')
print(f'[10-11] Padding: {pdu[10:12].hex()}')
print()
body = pdu[12:]
print('Body (84 bytes):')
print(f'[12-17] Emitting Entity ID: {body[0:6].hex()}')
print(f'[18-23] Target Entity ID: {body[6:12].hex()}')
print(f'[24-29] Munition ID: {body[12:18].hex()}')
print(f'[30-35] Event ID: {body[18:24].hex()}')
print(f'[36-39] Fire Mission Index: {body[24:28].hex()} = {struct.unpack(">I", body[24:28])[0]}')
print(f'[40-47] Location[0]: {body[28:36].hex()}')
print(f'[48-55] Location[1]: {body[36:44].hex()}')
print(f'[56-63] Location[2]: {body[44:52].hex()}')
print(f'[64-71] Weapon Type: {body[52:60].hex()}')
print(f'[72-73] Warhead: {body[60:62].hex()}')
print(f'[74-75] Fuse: {body[62:64].hex()}')
print(f'[76-77] Quantity: {body[64:66].hex()}')
print(f'[78-79] Rate: {body[66:68].hex()}')
print(f'[80-83] Velocity[0]: {body[68:72].hex()}')
print(f'[84-87] Velocity[1]: {body[72:76].hex()}')
print(f'[88-91] Velocity[2]: {body[76:80].hex()}')
print(f'[92-95] Range: {body[80:84].hex()}')