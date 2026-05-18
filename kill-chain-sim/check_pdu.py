from src.core.dis.fire_control import FireControl
from src.core.dis.dis_protocol import EntityId, DisTimestamp

fc = FireControl(exercise_id=1)
mission = fc.create_fire_mission(
    launcher_id=EntityId(25, 1, 1),
    target_id=EntityId(25, 1, 2),
    Munition_id=EntityId(25, 1, 1)
)
pdu_bytes = fc.build_fire_pdu_bytes(mission)
print(f'Total length: {len(pdu_bytes)}')
print(f'Hex: {pdu_bytes.hex()}')
print()
print('Structure:')
print(f'  Timestamp (4 bytes): {pdu_bytes[0:4].hex()}')
print(f'  Version (1 byte): {pdu_bytes[4]}')
print(f'  Exercise (1 byte): {pdu_bytes[5]}')
print(f'  PDU Type (1 byte): {pdu_bytes[6]}')
print(f'  Family (1 byte): {pdu_bytes[7]}')
print(f'  Length (2 bytes): {pdu_bytes[8:10].hex()} = {int.from_bytes(pdu_bytes[8:10], "big")}')
print(f'  Padding (2 bytes): {pdu_bytes[10:12].hex()}')
print(f'  Fire Data (30 bytes): {pdu_bytes[12:42].hex()}')