# Test entity ID byte patterns
import struct

# The last 2 bytes of the 6-byte entity ID = 9000 = entity = 36864
# This is correct (big-endian 0x9000 = 36864)

# For site and app, let's check: 47ae1400
# Could be 2 bytes (47 ae = site big-endian) + 2 bytes (14 00 = app big-endian)
b = bytes.fromhex('47ae')
print(f'47ae as big-endian uint16: {struct.unpack(">H", b)[0]}')  # 18350
print(f'47ae as little-endian uint16: {struct.unpack("<H", b)[0]}')  # 44599

b2 = bytes.fromhex('1400')
print(f'1400 as big-endian uint16: {struct.unpack(">H", b2)[0]}')  # 5120
print(f'1400 as little-endian uint16: {struct.unpack("<H", b2)[0]}')  # 20

# Wait, 5120 is what we're seeing for app! So:
# entity ID bytes: 47 ae 14 00 90 00
# Interpreted as: site=0x47ae=18350, app=0x1400=5120, entity=0x9000=36864 (big-endian)
# But AFSIM says Entity: 25:1:2

# Unless... AFSIM sends site=25 (0x0019), app=1 (0x0001), entity=2 (0x0002)
# 0x0019 0x0001 0x0002 packed as big-endian = 001900010002

# Our bytes: 47ae14009000
# Not matching any simple interpretation

# What if AFSIM encodes each 16-bit value in LITTLE-ENDIAN in the PDU?
# site=25 -> 19 00, app=1 -> 01 00, entity=2 -> 02 00
# But that's 001900010002 still doesn't match

# Actually wait - let me check the raw hex: 47ae14009000
# If we split as 2+2+2 bytes big-endian: 47ae, 1400, 9000
# 47ae = 18350, 1400 = 5120, 9000 = 36864

# These ARE the numbers we're seeing! So the parsing IS correct.
# The question is: why does AFSIM log "Entity: 25:1:2" if the actual bytes are different?

# I think I understand now: AFSIM's DIS output shows the "logical" entity ID (25:1:2)
# But the actual bytes transmitted are something different (maybe internal representation)

# OR: there's a mismatch between what AFSIM's "Created DIS entity" log says
# and what it actually puts in the PDU

# Let me check: 18350:5120:36864 in hex
# 18350 = 0x47AE, 5120 = 0x1400, 36864 = 0x9000
# All end in 0, which is suspicious

# What if this is a WSF-to-DIS entity ID mapping issue?
print("\n18350:5120:36864 = 0x47AE:0x1400:0x9000")
print("Entity field always ends in 0x9000 = 36864 = correct")
print("Site and app are varying (dynamic assignments?)")

# Check: are these values stable or changing?
# From logs: 18350, 27670, 28835 for site (all varying)
# 5120, 49152, 54784 for app (all varying)
# 36864 always = 0x9000

# So entity ID is being assigned dynamically by AFSIM
# Site and app IDs vary each update (or are they different entities?)
# The last field (entity=36864) is always the same

# Actually wait - entity=36864 = 0x9000. Could this be a DIS encoding of
# something like force_id or entity_type?

# Let me just confirm: site and app vary, entity stays at 0x9000
# This is NOT matching 25:1:2 at all
print("\nAFSIM claims Entity: 25:1:2")
print("But we're receiving: site=18350, app=5120, entity=36864")
print("This is a major DIS Entity ID mismatch!")