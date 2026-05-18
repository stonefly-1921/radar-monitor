# Test DIS Entity ID parsing with different byte orders
import struct

# Raw bytes from AFSIM - what we should get from EntityId.decode()
# site=25, app=1, entity=1 in big-endian (DIS standard)
correct_bytes = struct.pack('>HHH', 25, 1, 1)
print(f"Expected EntityId (big-endian): {correct_bytes.hex()} -> decoded as big-endian: ", end="")
site, app, entity = struct.unpack('>HHH', correct_bytes[:6])
print(f"site={site}, app={app}, entity={entity}")

# What if AFSIM sends little-endian instead?
wrong_bytes = struct.pack('<HHH', 25, 1, 1)
print(f"\nLittle-endian bytes: {wrong_bytes.hex()} -> decoded as big-endian: ", end="")
site2, app2, entity2 = struct.unpack('>HHH', wrong_bytes[:6])
print(f"site={site2}, app={app2}, entity={entity2}")

# The values we're seeing in logs: 62914:36352:36864
# Let's see what these are in binary
vals = [62914, 36352, 36864]
for v in vals:
    print(f"\n{v} = 0x{v:04X} = binary {v:016b}")

# Check if these could be site_id=25, app=1, entity=1 with some transformation
# 25 in little-endian = 0x0019 = 0000 0000 0001 1001
# 1 in little-endian = 0x0001 = 0000 0000 0000 0001
# 1 in little-endian = 0x0001

# What if we take the first 3 bytes of the 6-byte entity ID and interpret as uint16?
# Actually let me check what happens if AFSIM uses uint32 instead of uint16
vals_packed = struct.pack('<HHH', 62914, 36352, 36864)
print(f"\n62914:36352:36864 packed as little-endian 3x16: {vals_packed.hex()}")

# What if entity_id is being read from wrong offset in the PDU?
# Entity State PDU entity ID offset is byte 24 in the header
# Let's see: PDU header is 14 bytes (version=1, exercise=1, pdu_type=1, family=1, timestamp=5, length=2, padding=2)
# Entity ID starts at byte 24 (after: entity state kind(1), domain(1), country(2), etc.)
# Actually the full Entity State PDU structure has entity ID at offset 24

# Test: what if the first field (site) is read as uint32 instead of uint16?
site_from_4bytes = struct.unpack('<I', vals_packed[:4])[0]
print(f"\nFirst 4 bytes as uint32 little-endian: {site_from_4bytes} = 0x{site_from_4bytes:08X}")

# What about reading as uint16 from wrong position?
# If bytes are swapped
test = 25
print(f"\n25 as uint16 big-endian: {struct.pack('>H', test).hex()}")
print(f"25 as uint16 little-endian: {struct.pack('<H', test).hex()}")

# What if AFSIM stores site_id in upper byte?
# 25 << 8 = 6400 = 0x1900
print(f"\n25 << 8 = {25 << 8} = 0x{(25 << 8):04X}")

# And if we read this big-endian from the upper byte...
packed_25_shifted = struct.pack('>H', 25 << 8)
print(f"25 << 8 as big-endian uint16: {packed_25_shifted.hex()} = {struct.unpack('>H', packed_25_shifted)[0]}")

# Actually let me check the actual int values more carefully
print(f"\nChecking if 62914 could be 25 in disguise...")
print(f"25 = 0x{25:04X} = {25:016b}")
print(f"62914 = 0x{62914:04X} = {62914:016b}")

# XOR?
print(f"\n25 XOR 62914 = {25 ^ 62914} = 0x{(25 ^ 62914):04X}")

# Wait, maybe there's a bit rotation or something?
# Let me just check: if AFSIM sends entity ID as 3 consecutive uint16 in little-endian
# but we decode as big-endian, what do we get?
afsim_sends = struct.pack('<HHH', 25, 1, 1)  # AFSIM encodes as little-endian
decoded_wrong = struct.unpack('>HHH', afsim_sends)  # We decode as big-endian
print(f"\nAFSIM sends (LE): {afsim_sends.hex()} -> We decode as BE: {decoded_wrong}")

# Now what if AFSIM sends as big-endian but we decode as little-endian?
afsim_sends_be = struct.pack('>HHH', 25, 1, 1)
decoded_le = struct.unpack('<HHH', afsim_sends_be)
print(f"AFSIM sends (BE): {afsim_sends_be.hex()} -> We decode as LE: {decoded_le}")