"""
AFSIM DIS PDU Capture Test - Multi-Interface

Captures raw UDP packets from AFSIM multicast streams to diagnose what's being sent.
Listens on BOTH xio_interface multicast (235.7.11.27:3002) and dis_realtime (224.2.25.55:3225).
"""
import socket
import struct
import time
import sys
import threading
from collections import Counter


MULTICAST_GROUPS = [
    ("235.7.11.27", 3002, "xio_interface"),
    ("224.2.25.55", 3225, "dis_realtime"),
]
CAPTURE_SECONDS = 10


def try_parse_dis_header(data: bytes):
    """Try multiple DIS header formats to parse the packet."""
    if len(data) < 6:
        return [f"TOO SHORT ({len(data)} bytes)"]
    
    results = []
    
    # Try 6-byte minimal: version(1) + ex_id(1) + pdu_type(2) + family(2) = 6 bytes
    try:
        v, eid, ptype, fam = struct.unpack("!BBHH", data[:6])
        results.append(f"ver={v} ex={eid} type={ptype} family={fam}")
    except struct.error as e:
        results.append(f"FAIL_6B: {e}")
    
    # Try with timestamp and length (12 bytes standard DIS)
    if len(data) >= 12:
        try:
            v, eid, ptype, fam, ts, length = struct.unpack("!BBHHL", data[:12])
            results.append(f"STD12: ver={v} ex={eid} type={ptype} family={fam} ts={ts} len={length}")
        except struct.error as e:
            results.append(f"FAIL_12B: {e}")
    
    return results


def capture_thread(group: str, port: int, name: str, results: dict):
    """Capture packets on one multicast group."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.settimeout(0.2)
    
    try:
        sock.bind(("", port))
    except OSError:
        try:
            sock.bind((group, port))
        except OSError:
            pass
    
    try:
        mreq = struct.pack("!4s4s", socket.inet_aton(group), socket.inet_aton("0.0.0.0"))
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    except Exception as e:
        print(f"  [{name}] Could not join multicast {group}: {e}")
        sock.close()
        return
    
    packets = []
    start = time.time()
    
    try:
        while time.time() - start < CAPTURE_SECONDS:
            try:
                data, addr = sock.recvfrom(8192)
                packets.append((data, addr))
            except socket.timeout:
                continue
    except Exception:
        pass
    
    results[name] = (group, port, packets)
    sock.close()


def main():
    print(f"=== AFSIM RAW PDU Capture Test (Multi-Interface) ===")
    print(f"Listening on:")
    for g, p, n in MULTICAST_GROUPS:
        print(f"  {n}: {g}:{p}")
    print(f"Capturing for {CAPTURE_SECONDS} seconds...\n")

    results = {}
    threads = []
    
    for group, port, name in MULTICAST_GROUPS:
        t = threading.Thread(target=capture_thread, args=(group, port, name, results))
        t.start()
        threads.append(t)
    
    for t in threads:
        t.join()
    
    print("\n" + "="*60)
    print("RESULTS")
    print("="*60)
    
    total_all = 0
    for name, (group, port, packets) in results.items():
        print(f"\n--- {name} ({group}:{port}) ---")
        if not packets:
            print(f"  NO packets received")
            continue
        
        print(f"  {len(packets)} packets:")
        total_all += len(packets)
        
        for i, (data, addr) in enumerate(packets[:5]):
            print(f"\n  Packet #{i+1} from {addr} ({len(data)} bytes):")
            # Show first 48 bytes as hex
            hex_str = data[:48].hex()
            print(f"    Hex: {hex_str}")
            # Parse attempts
            parses = try_parse_dis_header(data)
            for p in parses:
                print(f"    Parse: {p}")
        
        if len(packets) > 5:
            print(f"\n  ... and {len(packets)-5} more packets")
    
    print(f"\n--- TOTAL: {total_all} packets across all interfaces ---")
    
    if total_all == 0:
        print("\n  *** NO PACKETS RECEIVED ***")
        print("  AFSIM may not be sending on any of the expected multicast groups")
        print("  Expected: 235.7.11.27:3002 (xio) or 224.2.25.55:3225 (dis_realtime)")
    
    return 0 if total_all == 0 else 1


if __name__ == "__main__":
    sys.exit(main())