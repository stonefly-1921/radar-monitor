#!/usr/bin/env python3
"""
test_dis_fire_params.py — 自动化测试 DIS Fire PDU 格式
策略: 发送不同参数组合，观察 AFSIM 的响应
"""
import socket
import struct
import time
import subprocess
import threading
import sys
import os

MULTICAST_ADDR = "239.1.2.3"
DIS_PORT = 3000
EXERCISE_ID = 1

# AFSIM DIS 配置
SITE = 1
APP = 1

def make_entity_id(site, app, entity):
    """DIS Entity ID: 3 x uint16 big-endian"""
    return struct.pack("!HHH", site, app, entity)

def make_pdu_header(pdu_type, length):
    """PDU header: 8 bytes (IEEE 1278.1)"""
    return struct.pack("!BBBBHH",
        pdu_type,     # 2 = Fire PDU
        7,            # protocol version
        EXERCISE_ID,  # exercise ID
        0,            # padding
        length,       # total length (big-endian)
        0             # padding
    )

def make_fire_pdu(firing_entity, target_entity, weapon_entity,
                  munition_kind=1, munition_domain=3, munition_country=1,
                  munition_category=1, munition_subcategory=0, munition_specific=0,
                  location=(0.0, 0.0, 0.0), velocity=(0.0, 0.0, 0.0)):
    """构造 DIS Fire PDU (IEEE 1278.1)"""
    # Burst descriptor: munition entity type (8 bytes) + warhead (2) + fuse (2) = 12 bytes
    burst_descriptor = struct.pack("!BBHBBBB",
        munition_kind, munition_domain, munition_country,
        munition_category, munition_subcategory, munition_specific, 0
    ) + struct.pack("!HH", 0, 0)  # warhead=0, fuse=0

    # Location: ECEF coordinates (3 x double = 24 bytes)
    location_bytes = struct.pack("!ddd", *location)

    # Velocity: 3 x float (12 bytes)
    velocity_bytes = struct.pack("!fff", *velocity)

    # Fire mission index (4 bytes)
    fire_mission_index = struct.pack("!I", 1)

    body = (firing_entity + target_entity + weapon_entity +
            fire_mission_index + burst_descriptor +
            location_bytes + velocity_bytes)

    total_length = 8 + len(body)  # header + body
    header = make_pdu_header(pdu_type=2, length=total_length)
    return header + body

def send_fire_pdu(sock, target_entity_id, weapon_entity_id,
                   munition_type=(1,3,1,1,0,0),
                   firing_entity_id=None):
    """发送 Fire PDU 到 AFSIM"""
    if firing_entity_id is None:
        firing_entity_id = make_entity_id(SITE, APP, 999)  # dummy firing entity

    pdu = make_fire_pdu(
        firing_entity=firing_entity_id,
        target_entity=target_entity_id,
        weapon_entity=weapon_entity_id,
        munition_kind=munition_type[0],
        munition_domain=munition_type[1],
        munition_country=munition_type[2],
        munition_category=munition_type[3],
        munition_subcategory=munition_type[4],
        munition_specific=munition_type[5],
        location=(6378137.0, 0.0, 0.0),  # ECEF
        velocity=(300.0, 0.0, 0.0)
    )

    sock.sendto(pdu, (MULTICAST_ADDR, DIS_PORT))
    print(f"Sent Fire PDU: firing={firing_entity_id.hex()[:12]} "
          f"target={target_entity_id.hex()[:12]} weapon={weapon_entity_id.hex()[:12]} "
          f"len={len(pdu)}")

def test_scenario(scenario_path, test_params):
    """运行单个 AFSIM 场景测试"""
    print(f"\n{'='*60}")
    print(f"Testing: {test_params['name']}")
    print(f"Params: {test_params}")
    print(f"Scenario: {scenario_path}")

    # 启动 AFSIM
    proc = subprocess.Popen(
        ["/d/afsim-2.9.0-win64/bin/mission.exe", scenario_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    # 等待启动
    time.sleep(2)

    # 创建 UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
    sock.setblocking(False)

    # 发送 Fire PDU
    try:
        send_fire_pdu(sock, **test_params['fire_params'])
    except Exception as e:
        print(f"Send error: {e}")

    # 收集 AFSIM 输出 5 秒
    output_lines = []
    start = time.time()
    while time.time() - start < 5:
        line = proc.stdout.readline()
        if line:
            output_lines.append(line.rstrip())
            if "TRACK" in line or "FIRE" in line or "Created" in line or "Error" in line:
                print(f"  AFSIM: {line.rstrip()}")
        if proc.poll() is not None:
            break

    proc.terminate()
    sock.close()
    return output_lines

def main():
    scenario = "/c/Users/15041/.openclaw/workspace/kill-chain-sim/src/sim/test_dis_fire.txt"

    tests = [
        {
            "name": "Test 1: Target=red_target_1 (entity 1), weapon entity 2, BLUE_SR_SAM munition",
            "fire_params": {
                "target_entity_id": make_entity_id(SITE, APP, 1),
                "weapon_entity_id": make_entity_id(SITE, APP, 2),
                "munition_type": (1, 3, 1, 1, 0, 0),
            }
        },
        {
            "name": "Test 2: Target=0:0:0 wildcard, weapon entity 3, BLUE_SR_SAM munition",
            "fire_params": {
                "target_entity_id": make_entity_id(0, 0, 0),
                "weapon_entity_id": make_entity_id(SITE, APP, 3),
                "munition_type": (1, 3, 1, 1, 0, 0),
            }
        },
        {
            "name": "Test 3: Unicast to 127.0.0.1 instead of multicast",
            "fire_params": {
                "target_entity_id": make_entity_id(SITE, APP, 1),
                "weapon_entity_id": make_entity_id(SITE, APP, 2),
                "munition_type": (1, 3, 1, 1, 0, 0),
            },
            "unicast": True,
        },
    ]

    print(f"AFSIM DIS Fire PDU 参数测试")
    print(f"目标: {MULTICAST_ADDR}:{DIS_PORT}")
    print(f"Exercise: {EXERCISE_ID}, Site:{SITE}, App:{APP}")

    for test in tests:
        test_scenario(scenario, test)
        time.sleep(1)

if __name__ == "__main__":
    main()
