Fire PDU hex from capture:
080000002406010201002b0000001900010001001900010002001900010001000000100064000200010000

Let me parse it byte by byte:

Offset 0-4 (5 bytes): Timestamp
  08 00 00 00 24

Offset 5-12 (8 bytes): Header
  06 01 02 01 00 2b 00 00

Offset 13-18 (6 bytes): Emitting entity ID
  00 19 00 01 00 01

Offset 19-24 (6 bytes): Target entity ID
  00 19 00 01 00 02

Offset 25-30 (6 bytes): Munition ID
  00 19 00 01 00 01

Offset 31-34 (4 bytes): Fire mission index
  00 00 10 00 = 4096

Offset 35-36 (2 bytes): Warhead
  64 00 = 100

Offset 37-38 (2 bytes): Fuse
  02 00 = 2

Offset 39-40 (2 bytes): Quantity
  00 01 = 1

Offset 41-42 (2 bytes): Rate
  00 00 = 0

Total: 43 bytes

Now let's analyze the timestamp issue:

The timestamp bytes are: 08 00 00 00 24

Our DisTimestamp.encode() uses format ">BI" where B=uint8, I=uint32:
- Byte 0: 0x08 = hours = 8
- Bytes 1-4: 0x00000024 = time = 36 (centiseconds)

AFSIM ERROR shows:
  Version: 8 (byte 5 = 0x08 from header is being read as version!)
  
Wait - if AFSIM is reading byte 0 (0x08) as protocol version, that means AFSIM is skipping the timestamp entirely and reading from the wrong offset!

This suggests AFSIM expects a DIFFERENT timestamp format - perhaps 4 bytes instead of 5?

Or maybe AFSIM expects the timestamp to be ABSENT/OMITTED for some PDUs?

Actually, looking at the DIS standard more carefully:
- Entity State PDU (Type 1) typically uses the full 5-byte timestamp
- Fire PDU (Type 2) might use a shorter timestamp or no timestamp at all

Let me check if the issue is that we're including a timestamp that AFSIM doesn't expect for Fire PDUs.
