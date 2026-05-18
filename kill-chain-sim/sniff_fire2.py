"""Sniff the actual Fire PDU being sent to the network."""
import socket
import struct

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.bind(('0.0.0.0', 3002))
sock.settimeout(0.5)

print("Listening for Fire PDUs on port 3002...")
count = 0
while count < 3:
    try:
        data, addr = sock.recvfrom(2000)
        if len(data) >= 14:
            pdu_type = data[7]
            if pdu_type == 2:
                print("\nFire PDU from " + str(addr))
                print("  Total length: " + str(len(data)) + " bytes")
                print("  Full hex: " + data.hex())
                ts = struct.unpack('>I', data[0:4])[0]
                length = struct.unpack('>H', data[8:10])[0]
                print("  Timestamp: " + str(ts))
                print("  Version: " + str(data[4]))
                print("  Exercise: " + str(data[5]))
                print("  PDU Type: " + str(data[6]))
                print("  Family: " + str(data[7]))
                print("  Length field: " + str(length))
                count += 1
    except socket.timeout:
        if count > 0:
            break

sock.close()
print("\nDone")