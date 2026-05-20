#!/usr/bin/env python
import sys
sys.path.insert(0, '.')
from src.core.shared_mem.shm_client import ShmClient, CmdType, SensorMode

shm = ShmClient('kill_chain_shm')
ok = shm.connect()
print('connect:', ok)
if ok:
    h = shm._read_header()
    print('before: cmd_in=', h.cmd_in)
    cmd_id = shm.send_sensor_control(sensor_id=1, mode=SensorMode.TRACK)
    print('wrote cmd_id:', cmd_id)
    h = shm._read_header()
    print('after: cmd_in=', h.cmd_in)
    shm.close()
