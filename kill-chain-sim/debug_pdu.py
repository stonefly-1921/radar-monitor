import struct

# Our Fire PDU (100 bytes total with 88-byte body)
our_pdu = bytes.fromhex(
    '00000435060102010064000000'
    '1900010001'
    '1900010002'
    '1900010001'
    '000000000000'
    '00000001'
    '00000000000000000000000000000000'
    '0000000000000000'
    '00640002'
    '00010000'
    '000000000000000000000000'
    '00000000'
    '00000000'
)

print('Our Fire PDU (100 bytes):')
print('  Total:', len(our_pdu), 'bytes')
print()
print('Header breakdown:')
print('  Bytes 0-3 (timestamp):', our_pdu[0:4].hex(), '=', struct.unpack('>I', our_pdu[0:4])[0])
print('  Byte 4 (version):', our_pdu[4], '(expected: 6)')
print('  Byte 5 (exercise):', our_pdu[5], '(expected: 1)')
print('  Byte 6 (type):', our_pdu[6], '(expected: 2 for Fire)')
print('  Byte 7 (family):', our_pdu[7], '(expected: 1 for Warfare)')
print('  Bytes 8-9 (length):', our_pdu[8:10].hex(), '=', struct.unpack('>H', our_pdu[8:10])[0], '(expected: 100)')
print('  Bytes 10-11 (padding):', our_pdu[10:12].hex())
print()
print('If AFSIM uses 5-byte timestamp:')
print('  AFSIM reads bytes 0-4 as timestamp')
print('  AFSIM reads byte 5 as version')
print('    Our byte 5 =', our_pdu[5], '(should be 6)')
print('    Our byte 6 =', our_pdu[6], '(should be 1 for exercise)')
print('    Our byte 7 =', our_pdu[7], '(should be 2 for type)')
print('    Our byte 8 =', our_pdu[8], '(should be 1 for family)')

print()
print('Entity State PDU from AFSIM has:')
print('  Byte 4 = 1')
print('  Byte 5 = 1')
print('  Byte 6 = 1')
print('  Byte 7 = 4 (type=EntityState?)')
print()
print('That suggests header offset for EntityState is same as ours')
print('So the problem is not in header format')