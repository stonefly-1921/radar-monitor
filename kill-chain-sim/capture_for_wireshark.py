"""Capture both our Fire PDU and AFSIM's response for Wireshark analysis."""
import socket
import struct
import time

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.bind(('0.0.0.0', 3002))
sock.settimeout(3)

print("Listening for 30 seconds...")
print("Send Fire PDU manually or run kill-chain-sim")
print("")

start = time.time()
captured = []

while time.time() - start < 30:
    try:
        data, addr = sock.recvfrom(2000)
        if len(data) >= 12:
            pdu_type = data[7] if len(data) > 7 else -1
            ts = struct.unpack('>I', data[0:4])[0] if len(data) >= 4 else 0
            length = struct.unpack('>H', data[8:10])[0] if len(data) >= 10 else 0
            version = data[4] if len(data) > 4 else 0
            exercise = data[5] if len(data) > 5 else 0
            
            entry = {
                'time': time.time() - start,
                'from': addr,
                'len': len(data),
                'hex': data.hex(),
                'type': pdu_type,
                'version': version,
                'exercise': exercise,
                'length': length,
                'timestamp': ts
            }
            captured.append(entry)
            
            print(f"[{entry['time']:.1f}s] {addr[0]}:{addr[1]} len={len(data)} "
                  f"type={pdu_type} ver={version} ex={exercise} length={length} ts={ts}")
            
            # For Fire PDUs, show extra detail
            if pdu_type == 2 and len(data) >= 96:
                print(f"  -> Fire PDU: emitting={data[12:18].hex()} target={data[24:30].hex()}")
            
            # For unknown types, show hex snippet
            if pdu_type not in [1, 2, 3] and pdu_type != -1:
                print(f"  -> Unknown type! Hex: {data[:30].hex()}")
                
    except socket.timeout:
        if len(captured) > 0:
            break

sock.close()

print(f"\n\nCaptured {len(captured)} PDUs")
print("For Wireshark: filter 'udp.port == 3002'")