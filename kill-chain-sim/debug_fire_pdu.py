from src.core.dis.dis_protocol import FirePdu, EntityId, EntityType

pdu = FirePdu(
    fire_mission_index=1,
    emitting_entity_id=EntityId(25, 1, 1),
    target_entity_id=EntityId(25, 1, 2),
    Munition_id=EntityId(25, 1, 1),
    event_id=EntityId(0, 0, 0),
    location=(0.0, 0.0, 0.0),
    weapon_type=EntityType(0, 0, 0, 0, 0, 0, 0),
    warhead=100,
    fuse=2,
    quantity=1,
    rate=0,
    velocity=(0.0, 0.0, 0.0),
    range_val=0.0
)

encoded = pdu.encode()
print(f"Encoded length: {len(encoded)} bytes (expected 84)")
print(f"Hex: {encoded.hex()}")
print()
print("Expected structure (84 bytes):")
print("  emitting_entity_id: 6 bytes")
print("  target_entity_id: 6 bytes")
print("  Munition_id: 6 bytes")
print("  event_id: 6 bytes")
print("  fire_mission_index: 4 bytes")
print("  location: 24 bytes")
print("  weapon_type: 8 bytes")
print("  warhead, fuse, quantity, rate: 8 bytes")
print("  velocity: 12 bytes")
print("  range_val: 4 bytes")
print(f"  Total: {6*4 + 4 + 24 + 8 + 8 + 12 + 4} bytes")