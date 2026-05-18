from src.core.dis.dis_protocol import EntityId

# Expected DIS entity IDs
print("Expected Entity ID: site=25, app=1, entity=1")

# Values from AFSIM (what we're seeing)
vals = [62914, 36352, 36864]
for v in vals:
    b = v.to_bytes(2, 'little')
    import struct
    big_endian = struct.unpack('>H', b)[0]
    print(f'{v} -> little-endian bytes {b.hex()} -> big-endian read {big_endian}')

# So AFSIM sends: EntityId(site_id=25, app=1, entity=1)
# Which as little-endian 16-bit becomes: 25=0x0019, 1=0x0001, 1=0x0001
# But in a PDU when these are encoded in DIS standard order (big-endian 16-bit per field),
# site=0x0019, app=0x0001, entity=0x0001 -> these don't match the large numbers above

# Actually, let's check: maybe AFSIM sends EntityId as 3 x uint32 (big-endian)?
eid = EntityId(site_id=25, application_id=1, entity_id=1)
encoded = eid.encode()  # this returns the 6-byte little-endian representation
print(f"25:1:1 encoded (6 bytes): {encoded.hex()}")
print(f"As 3x uint32 big-endian: {struct.unpack('>HHH', encoded)}")