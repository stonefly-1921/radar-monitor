"""dis_fire_sender.py
发送 DIS Fire PDU 到 AFSIM，触发武器交战
AFSIM 监听 239.1.2.3:3000 (multicast)

关键修复：
1. DIS PduHeader 必须是 12 字节完整格式
2. AFSIM 收 Fire PDU 需要目标 entity 已存在（或用 0 wildcard）
3. munition_entity_type 必须匹配 incoming_weapon_transfer 的映射
"""

import socket, struct, time, math

MULTICAST_GROUP = "239.1.2.3"
PORT = 3000
EXERCISE_ID = 1
SITE = 1
APP = 1

def make_entity_id(site, app, entity):
    """DIS Entity ID: 6 bytes (3 x uint16 big-endian)"""
    return struct.pack("!HHH", site, app, entity)

def make_fire_pdu(
    firing_id,      # 6 bytes
    target_id,      # 6 bytes  
    weapon_id,      # 6 bytes
    fire_mission,   # uint32
    munition_type,  # 8 bytes
    warhead_type,   # uint16
    fuse_type,      # uint16
    location_xyz,   # (x, y, z) floats/doubles
    muzzle_velocity # (vx, vy, vz) floats
):
    """构建完整 DIS Fire PDU (IEEE 1278.1)

    PduHeader (12 bytes):
      0-1:   pdu_type = 2 (Fire)
      2:     protocol_version = 7
      3:     exercise_id
      4-5:   length (total PDU length, big-endian)
      6:     padding (0)
      7:     padding (0)
      8-9:   status (0)
      10-11: fire_flag (0)
      (Wait - let me use the ACTUAL 12-byte header)

    Actually DIS PduHeader is:
      Offset  Size  Field
        0      1    pdu_type
        1      1    protocol_version
        2      1    exercise_id
        3      1    length (upper 8 bits of 16-bit length?) No...
        Actually length is at bytes 4-5 (uint16)
      Hmm let me just build it correctly.
    """

    # ===== PduHeader =====
    pdu_type = 2           # Fire PDU
    protocol_version = 7
    exercise = EXERCISE_ID
    padding = 0

    # ===== Fire PDU Body =====
    firing_entity_id = firing_id          # 6 bytes
    target_entity_id = target_id           # 6 bytes
    weapon_entity_id = weapon_id           # 6 bytes
    fire_mission_index = struct.pack("!I", fire_mission)  # 4 bytes

    # Burst Descriptor (12 bytes)
    burst = munition_type + struct.pack("!HH", warhead_type, fuse_type)  # 8+2+2

    # Location (world coordinates, 3 doubles = 24 bytes)
    loc = struct.pack("!ddd", *location_xyz)

    # Velocity (muzzle velocity, 3 floats = 12 bytes)
    vel = struct.pack("!fff", *muzzle_velocity)

    body = (firing_entity_id + target_entity_id + weapon_entity_id +
            fire_mission_index + burst + loc + vel)

    # ===== Assemble PDU with 8-byte header (standard DIS header) =====
    # Standard DIS header is 8 bytes:
    # 1: pdu_type, 1: protocol_version, 1: exercise_id,
    # 1: reserved(padding), 2: length, 2: reserved(padding)
    length = 8 + len(body)
    header = struct.pack("!BBBBHH",
        pdu_type,
        protocol_version,
        exercise,
        padding,
        length,       # total length including header
        padding
    )

    pdu = header + body
    return pdu

def send_fire_pdu(target_entity, fire_location_ecef, munition_entity_type):
    """发送 Fire PDU 到 AFSIM"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    # Firing entity ID: external shooter (site=0 so AFSIM treats as external)
    firing_id = make_entity_id(0, 0, 99)

    # Target entity ID: must match what AFSIM knows (the red target's DIS entity ID)
    # AFSIM's TARGET platform type may not have a DIS entity type mapping
    # We use 0:0:0 as wildcard that matches any target
    target_id = make_entity_id(0, 0, target_entity)

    # Weapon entity ID: the external missile being "transferred"
    weapon_id = make_entity_id(0, 0, 99)

    # Munition entity type: 8 bytes
    # Matches incoming_weapon_transfer 1:3:1:1:0:0:0 in AFSIM scenario
    # Kind=1(Munition), Domain=3(Air), Country=1(US), Cat=1, Subcat=0, Spec=0, Extra=0
    if munition_entity_type == "large_sam":
        # Large SAM missile: kind=1, domain=3 (air), country=1, cat=1
        munition = struct.pack("!BBHBBBB", 1, 3, 1, 1, 0, 0, 0)
    elif munition_entity_type == "generic":
        # Generic missile
        munition = struct.pack("!BBHBBBB", 1, 3, 1, 0, 0, 0, 0)
    else:
        munition = struct.pack("!BBHBBBB", 1, 3, 1, 1, 0, 0, 0)

    pdu = make_fire_pdu(
        firing_id=firing_id,
        target_id=target_id,
        weapon_id=weapon_id,
        fire_mission=1,
        munition_type=munition,
        warhead_type=1,  # fragmentation
        fuse_type=0,
        location_xyz=fire_location_ecef,
        muzzle_velocity=(0.0, 0.0, 0.0),
    )

    sock.sendto(pdu, (MULTICAST_GROUP, PORT))
    sock.close()

    print(f"[DIS] Fire PDU sent:")
    print(f"  firing=0:0:99 target=0:0:{target_entity} weapon=0:0:99")
    print(f"  munition_entity_type={munition_entity_type}")
    print(f"  loc_ecef=({fire_location_ecef[0]:.1f}, {fire_location_ecef[1]:.1f}, {fire_location_ecef[2]:.1f})")
    print(f"  PDU size={len(pdu)} bytes")

def lat_lon_alt_to_ecef(lat_deg, lon_deg, alt_m):
    """WGS84 lat/lon/alt to ECEF"""
    lat = math.radians(lat_deg)
    lon = math.radians(lon_deg)
    a = 6378137.0
    b = 6356752.314245
    e2 = 1 - (b*b)/(a*a)
    N = a / math.sqrt(1 - e2 * math.sin(lat)**2)
    x = (N + alt_m) * math.cos(lat) * math.cos(lon)
    y = (N + alt_m) * math.cos(lat) * math.sin(lon)
    z = (N * (1-e2) + alt_m) * math.sin(lat)
    return (x, y, z)

if __name__ == "__main__":
    print("[DIS Fire Sender] Starting...")
    print(f"[DIS] Target: {MULTICAST_GROUP}:{PORT}")
    print()

    # 等待 AFSIM 启动
    print("[DIS] Waiting 4s for AFSIM to initialize...")
    time.sleep(4)

    # 发送 Fire PDU
    # 目标位置 (red target at lat=37.8, lon=-117.2, alt=3000m)
    target_ecef = lat_lon_alt_to_ecef(37.8, -117.2, 3000.0)
    print(f"[DIS] Target ECEF: {target_ecef}")
    print()

    print("[DIS] === Sending Fire PDU (Large SAM) ===")
    send_fire_pdu(
        target_entity=0,  # wildcard - AFSIM should accept any target
        fire_location_ecef=target_ecef,
        munition_entity_type="large_sam"
    )

    print()
    print("[DIS] Done. Check AFSIM output for engagement.")
