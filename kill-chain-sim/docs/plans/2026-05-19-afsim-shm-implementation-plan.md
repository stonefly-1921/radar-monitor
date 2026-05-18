# AFSIM 共享内存接口实现计划

**日期：** 2026-05-19  
**前置：** 设计文档 `2026-05-19-afsim-shm-interface-design.md`

---

## 任务 1：Python ShmClient 实现

**文件：** `src/core/shared_mem/shm_client.py`

### 1.1 定义 ctypes 结构体（对应 C header）

```python
import ctypes
import mmap
import struct
import time
from pathlib import Path
from typing import List, Optional

# 枚举值
class TargetType(ctypes.c_uint8):
    AIRCRAFT, MISSILE, UCAV, JAMMER, UNKNOWN = 0, 1, 2, 3, 255

class SensorMode(ctypes.c_uint8):
    OFF, STANDBY, SEARCH, TRACK, JAMMING = 0, 1, 2, 3, 4

class WeaponStatus(ctypes.c_uint8):
    READY, LAUNCHED, INTERCEPTING, DEPLETED = 0, 1, 2, 3

class CmdType(ctypes.c_uint8):
    NONE, SENSOR_CONTROL, WEAPON_ASSIGN, TARGET_PRIORITY, PLATFORM_MOVE = 0, 1, 2, 3, 4

# 结构体（与 C shm_types.h 完全对应）
class ShmHeader(ctypes.Structure):
    _fields_ = [
        ("magic", ctypes.c_uint32),
        ("version", ctypes.c_uint16),
        ("track_count", ctypes.c_uint16),
        ("timestamp_ms", ctypes.c_uint32),
        ("cmd_in", ctypes.c_uint32),
        ("cmd_out", ctypes.c_uint32),
        ("afsim_ready", ctypes.c_uint8),
        ("padding", ctypes.c_uint8 * 7),
        ("fence", ctypes.c_uint64),
    ]

class TrackEntry(ctypes.Structure):
    _fields_ = [
        ("track_id", ctypes.c_uint32),
        ("lat", ctypes.c_double),
        ("lon", ctypes.c_double),
        ("altitude", ctypes.c_double),
        ("velocity", ctypes.c_double),
        ("heading", ctypes.c_double),
        ("timestamp_ms", ctypes.c_double),
        ("type", ctypes.c_uint8),
        ("force", ctypes.c_uint8),
        ("track_quality", ctypes.c_uint8),
        ("padding", ctypes.c_uint16),
    ]

class SensorEntry(ctypes.Structure):
    _fields_ = [
        ("sensor_id", ctypes.c_uint32),
        ("name", ctypes.c_char * 24),
        ("lat", ctypes.c_double),
        ("lon", ctypes.c_double),
        ("altitude", ctypes.c_double),
        ("mode", ctypes.c_uint8),
        ("side", ctypes.c_uint8),
        ("padding", ctypes.c_uint8 * 6),
        ("timestamp_ms", ctypes.c_double),
    ]

class WeaponEntry(ctypes.Structure):
    _fields_ = [
        ("weapon_id", ctypes.c_uint32),
        ("name", ctypes.c_char * 24),
        ("platform_id", ctypes.c_uint32),
        ("lat", ctypes.c_double),
        ("lon", ctypes.c_double),
        ("altitude", ctypes.c_double),
        ("status", ctypes.c_uint8),
        ("side", ctypes.c_uint8),
        ("padding", ctypes.c_uint8 * 6),
        ("timestamp_ms", ctypes.c_double),
    ]

class CmdEntry(ctypes.Structure):
    _fields_ = [
        ("cmd_id", ctypes.c_uint32),
        ("type", ctypes.c_uint8),
        ("sender_id", ctypes.c_uint32),
        ("target_id", ctypes.c_uint32),
        ("param1", ctypes.c_uint32),
        ("param2", ctypes.c_uint32),
        ("param3", ctypes.c_double),
        ("acknowledged", ctypes.c_uint8),
        ("padding", ctypes.c_uint8 * 7),
        ("timestamp_ms", ctypes.c_uint32),
    ]
```

### 1.2 ShmClient 类

```python
class ShmClient:
    MAGIC = 0x4B494C4C
    FENCE_VALUE = 0xDEADBEEFDEADBEEF
    MAX_TRACKS = 512
    MAX_CMDS = 256
    
    HEADER_SIZE = 128
    TRACK_SIZE = ctypes.sizeof(TrackEntry)   # 72 bytes
    CMD_SIZE = ctypes.sizeof(CmdEntry)        # 44 bytes

    def __init__(self, shm_name: str = "kill_chain_shm"):
        self.shm_name = shm_name
        self.fd = None
        self.mm = None
        self._header: Optional[ShmHeader] = None

    def connect(self) -> bool:
        """连接到共享内存"""
        path = Path("C:/Users/15041/.openclaw/workspace/kill-chain-sim") / f"{self.shm_name}.dat"
        try:
            self.fd = os.open(str(path), os.O_RDWR | os.O_CREAT, 0o666)
            os.ftruncate(self.fd, 64 * 1024 * 1024)  # 64 MB
            self.mm = mmap.mmap(self.fd, 0)
            # 初始化 header
            header = ShmHeader()
            header.magic = self.MAGIC
            header.version = 1
            self._write_header(header)
            return True
        except Exception as e:
            return False

    def get_tracks(self) -> List[TrackEntry]:
        """读取所有航迹"""
        header = self._read_header()
        if not header or header.magic != self.MAGIC:
            return []
        tracks = []
        for i in range(min(header.track_count, self.MAX_TRACKS)):
            offset = self.HEADER_SIZE + i * self.TRACK_SIZE
            track = self._read_track(offset)
            tracks.append(track)
        return tracks

    def send_command(self, cmd: CmdEntry) -> bool:
        """发送指令到 AFSIM"""
        header = self._read_header()
        idx = header.cmd_in % self.MAX_CMDS
        offset = self.HEADER_SIZE + self.MAX_TRACKS * self.TRACK_SIZE + idx * self.CMD_SIZE
        self._write_cmd(offset, cmd)
        header.cmd_in += 1
        self._write_header(header)
        return True

    def poll_commands_ack(self, timeout_ms: int = 1000) -> List[CmdEntry]:
        """轮询指令回执"""
        # 实现等待 ack 的逻辑
```

### 1.3 测试文件

**文件：** `tests/unit/test_shm_client.py`

```python
def test_shm_client_connect_and_read():
    client = ShmClient("test_kill_chain_shm")
    assert client.connect() == True
    
def test_write_and_read_track():
    client = ShmClient("test_kill_chain_shm")
    # 写入 TrackEntry，读取验证字段一致
    
def test_command_roundtrip():
    client = ShmClient("test_kill_chain_shm")
    # 写 CmdEntry，等待 ack，验证 cmd_id 一致
```

---

## 任务 2：AFSIM 脚本输出测试

**目的：** 验证 AFSIM 的 `writeln` 能否输出航迹信息到文件

### 2.1 测试场景

**文件：** `src/sim/test_track_output.txt`

```cui
# 最小化测试：验证脚本输出航迹
define_path_variable CASE test_track_output
log_file output/test_track_output.log

realtime

include D:\afsim-2.9.0-win64\demos\iads\setup.txt

# 最小场景：1个雷达阵地 + 1个蓝方 UCAV
platform 1_radar_company RADAR_COMPANY
  side red
  commander 10_iads_cmdr
  position 38:41:35n 117:05:57w altitude 0.0 m agl
end_platform

platform 2910_acq_radar ACQ_RADAR
  side red
  commander 2900_large_sam_battalion
  position 38:21:06n 117:28:44w altitude 0.0 m agl
  edit sensor acq_radar
     on
  end_sensor
end_platform

platform 100_ucav UCAV
   side blue
   commander SELF
   position 38:16:36n 116:19:48w altitude 35000 ft msl
   route
      navigation
         position 38:16:36n 116:19:48w altitude 35000 ft msl
         position 38:10:24n 117:02:48w altitude 35000 ft msl
      end_navigation
   end_route
end_platform

# 脚本：每 1 秒输出所有航迹信息到文件
processor track_output_test WSF_TRACK_PROCESSOR
   evaluation_interval 1.0 sec
   
   state ANY
      script void on_update()
         foreach (WsfPlatform p in PLATFORM.Subordinates())
         {
            foreach (WsfTrack t in p.Tracks())
            {
               writeln("TRACK: ", t.TrackId(), " lat=", t.Lat(), " lon=", t.Lon(),
                       " alt=", t.Altitude(), " vel=", t.Velocity(), " hdg=", t.Heading())
            }
         }
      end_script
   end_state
end_processor

end_time 2 min
```

### 2.2 测试步骤

1. 写 `src/sim/test_track_output.txt`
2. 启动 AFSIM
3. 检查 `output/test_track_output.log` 是否有 TRACK 输出
4. 验证输出格式是否符合预期

### 2.3 验证成功标准

- 日志文件包含 `TRACK:` 行
- 每行包含 track_id, lat, lon, altitude, velocity, heading
- 每秒至少 1 行输出

---

## 任务 3：联调测试

**前提：** 任务 1 和 2 都成功

### 3.1 集成测试场景

把 AFSIM 脚本输出改为写入共享内存格式文件，Python 监控该文件并写入共享内存。

### 3.2 验证项

| 验证项 | 成功标准 |
|---|---|
| Python 读取航迹 | 读到 lat/lon/alt/velocity/heading 非零 |
| Python 发送指令 | AFSIM 日志显示接收到指令 |
| 端到端延迟 | < 1 秒 |

---

## 任务依赖关系

```
任务1 (ShmClient)          任务2 (AFSIM脚本测试)
      \                          /
       \                        /
        \______________________/
                    |
               任务3 (联调)
```