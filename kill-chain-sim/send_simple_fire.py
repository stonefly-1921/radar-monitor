import socket
import struct

# Simple Fire PDU test
body = (
    b'\x00\x19\x00\x01\x00\x01' +
    b'\x00\x19\x00\x01\x00\x02' +
    b'\x00\x19\x00\x01\x00\x01' +
    b'\x00\x00\x00\x00\x00\x00' +
    b'\x00\x00\x00\x01' +
    b'\x00' * 24 +
    b'\x00' * 8 +
    b'\x00\x64\x00\x02' +
    b'\x00\x01\x00\x00' +
    b'\x00' * 12 +
    b'\x00' * 4 +
    b'\x00' * 4
)

header = struct.pack('>I', 0)
header += struct.pack('>BBBBHH', 6, 1, 2, 1, 0, 0)

total_len = 12 + len(body)
header = header[:8] + struct.pack('>H', total_len) + header[10:]

pdu = header + body

print('Fire PDU:', len(pdu), 'bytes')
print('Hex:', pdu.hex())

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
sock.sendto(pdu, ('192.168.3.255', 3002))
sock.close()
print('Sent')