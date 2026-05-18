"""Simple Fire PDU sender for Wireshark capture."""
import socket
import struct
import time

# Fire PDU bytes (96 bytes, verified earlier)
fire_pdu = bytes.fromhex(
    "00000975060102010060000000"
    "001900010001"  # emitting
    "001900010002"  # target
    "001900010001"  # Munition
    "000000000000"  # event
    "00000001"      # fire_mission_index
    "00000000000000000000000000000000"  # location (24 bytes)
    "0000000000000000"  # weapon_type (8 bytes)
    "00640002"      # warhead, fuse
    "00010000"      # quantity, rate
    "000000000000000000000000"  # velocity (12 bytes)
    "00000000"      # range
)

print(f"Fire PDU length: {len(fire_pdu)} bytes")
print(f"Hex: {fire_pdu.hex()}")

# Send to broadcast address (like our main code does)
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
sock.bind(('0.0.0.0', 3003))  # Different port to avoid conflict
sock.settimeout(1)

# Send to AFSIM
target = ('192.168.3.255', 3002)
print(f"\nSending to {target}...")
sent = sock.sendto(fire_pdu, target)
print(f"Sent {sent} bytes")

# Also send directly to AFSIM
direct = ('192.168.3.10', 3002)
print(f"\nSending directly to {direct}...")
sent = sock.sendto(fire_pdu, direct)
print(f"Sent {sent} bytes")

sock.close()
print("\nDone - check Wireshark on port 3002")