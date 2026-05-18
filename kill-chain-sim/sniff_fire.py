import socket
import struct
import threading
import time

# Create a raw socket to capture Fire PDUs
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.bind(('0.0.0.0', 3002))
sock.settimeout(0.5)

print("Listening for Fire PDUs on port 3002...")
start = time.time()
fire_pdus = []

while time.time() - start < 5:
    try:
        data, addr = sock.recvfrom(1500)
        if len(data) > 20:
            pdu_type = data[7]  # PDU type offset in DIS header
            version = data[5]   # Protocol version
            if pdu_type == 2:  # Fire PDU
                print(f"\nFire PDU from {addr}:")
                print(f"  Version: {version}, Type: {pdu_type}")
                print(f"  Total length: {len(data)}")
                print(f"  Full hex: {data.hex()}")
                # Parse entity IDs from Fire PDU
                # Timestamp (5) + header (8) = 13 bytes before entity IDs
                # Fire PDU body: emitting(6) + target(6) + munition(6) + ...
                if len(data) >= 25:
                    emitting = data[13:19]
                    target = data[19:25]
                    print(f"  Emitting entity: {emitting.hex()} = {struct.unpack('>HHH', emitting)}")
                    print(f"  Target entity: {target.hex()} = {struct.unpack('>HHH', target)}")
                fire_pdus.append(data)
    except socket.timeout:
        continue

print(f"\nCaptured {len(fire_pdus)} Fire PDUs")
sock.close()
