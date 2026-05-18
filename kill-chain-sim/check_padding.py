"""Check Fire PDU alignment - 84 bytes body might need padding to 88."""
import struct

# Our current body (84 bytes)
body_84 = (
    b'\x00\x19\x00\x01\x00\x01'  # emitting_entity_id (6)
    b'\x00\x19\x00\x01\x00\x02'  # target_entity_id (6)
    b'\x00\x19\x00\x01\x00\x01'  # Munition_id (6)
    b'\x00\x00\x00\x00\x00\x00'  # event_id (6)
    b'\x00\x00\x00\x01'          # fire_mission_index (4)
    b'\x00' * 24                 # location (24)
    b'\x00' * 8                  # weapon_type (8)
    b'\x00\x64\x00\x02'          # warhead, fuse (4)
    b'\x00\x01\x00\x00'          # quantity, rate (4)
    b'\x00' * 12                 # velocity (12)
    b'\x00' * 4                  # range (4)
)
print(f"Body size: {len(body_84)} bytes")

# AFSIM might expect 88 bytes - let's see what's missing
# If AFSIM reads 88 bytes from our 96-byte PDU:
# Header = 12, body = 84
# But if AFSIM expects 88-byte body:
# Total should be 100 bytes

# Let's check what a 100-byte Fire PDU would look like
# 4 (timestamp) + 8 (header fields) + 88 (body) = 100

print("\nPossible issue: AFSIM expects 88-byte body but we send 84")
print("Difference: 4 bytes")

# Let's see if there are any optional fields
# In some DIS implementations, Fire PDU has:
# - optional location (3 doubles = 24 bytes, but we have this)
# - optional velocity (3 floats = 12 bytes, but we have this)
# - optional "padding" to 8-byte boundary

# Actually, 84 + 4 = 88 (padding to 8-byte boundary)
body_88 = body_84 + b'\x00\x00\x00\x00'  # 4 bytes padding
print(f"\nIf we add 4 bytes padding: {len(body_88)} bytes")
print(f"Total PDU would be: 4 + 8 + {len(body_88)} = {4 + 8 + len(body_88)} bytes")