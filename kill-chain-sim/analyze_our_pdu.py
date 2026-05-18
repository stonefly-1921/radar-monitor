"""Analyze Fire PDU format by comparing with AFSIM source."""
import struct

# Our current Fire PDU hex (captured)
our_fire_pdu_hex = "000009750601020100600000001900010001001900010002001900010001000000000000000000010000000000000000000000000000000000000000000000000000000000000000006400020001000000000000000000000000000000000000"

data = bytes.fromhex(our_fire_pdu_hex)
print("Our Fire PDU Analysis:")
print(f"Total length: {len(data)} bytes (expected: 96)")
print()
print("Header (12 bytes):")
ts = struct.unpack('>I', data[0:4])[0]
print(f"  [0-3] Timestamp: {data[0:4].hex()} = {ts} seconds")
print(f"  [4]   Version: {data[4]} (expected: 6)")
print(f"  [5]   Exercise: {data[5]} (expected: 1)")
print(f"  [6]   PDU Type: {data[6]} (expected: 2 for Fire)")
print(f"  [7]   Family: {data[7]} (expected: 1 for Warfare)")
length = struct.unpack('>H', data[8:10])[0]
print(f"  [8-9] Length: {data[8:10].hex()} = {length} (expected: 96)")
print(f"  [10-11] Padding: {data[10:12].hex()} (expected: 0000)")
print()
print("Body (84 bytes expected):")
print(f"  [12-17] Emitting Entity ID: {data[12:18].hex()}")
print(f"          = {struct.unpack('>HHH', data[12:18])} (site, app, entity)")
print(f"  [18-23] Target Entity ID: {data[18:24].hex()}")
print(f"          = {struct.unpack('>HHH', data[24:30])}")
print(f"  [24-29] Munition ID: {data[24:30].hex()}")
print(f"  [30-35] Event ID: {data[30:36].hex()}")
print(f"  [36-39] Fire Mission Index: {data[36:40].hex()}")
print(f"  [40-63] Location (24 bytes): {data[40:64].hex()}")
print(f"  [64-71] Weapon Type (8 bytes): {data[64:72].hex()}")
print(f"  [72-75] Warhead(2), Fuse(2): {data[72:76].hex()}")
print(f"  [76-79] Quantity(2), Rate(2): {data[76:80].hex()}")
print(f"  [80-91] Velocity (12 bytes): {data[80:92].hex()}")
print(f"  [92-95] Range (4 bytes): {data[92:96].hex()}")
print()

# Check what AFSIM is seeing
print("\nWhat AFSIM sees (after header parsing):")
print(f"  Version: {data[4]} (but AFSIM sees 0 - header shifted?)")
print(f"  Type: {data[6]} (but AFSIM sees 9 - offset by 1?)")
print()
print("If AFSIM reads timestamp as 4 bytes but then looks for version at wrong offset...")
print(f"  At byte 5: version = {data[5]} (should be 6)")
print(f"  At byte 6: exercise = {data[6]} (should be 1)")
print(f"  At byte 7: pdu_type = {data[7]} (should be 2)")
print(f"  At byte 8: family = {data[8]} (should be 1)")
print(f"  At byte 9-10: length = {data[9:11].hex()}")