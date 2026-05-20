#!/usr/bin/env python
import sys
sys.path.insert(0, '.')
from src.core.shared_mem.shm_client import ShmClient

shm = ShmClient('kill_chain_shm')
ok = shm.connect()
print('connect:', ok)
if ok:
    h = shm._read_header()
    print('tracks:', h.track_count, 'ts:', h.timestamp_ms)
    for i in range(min(h.track_count, 3)):
        t = shm._read_track(128 + i * 72)
        print(f'  Track {i}: id={t.track_id}, lat={t.lat:.4f}, lon={t.lon:.4f}, alt={t.altitude:.0f}m')
    shm.close()
