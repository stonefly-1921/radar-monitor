# AFSIM 双向共享内存接口设计方案

**日期：** 2026-05-19  
**目标：** 通过共享内存实现 AFSIM 与 Python 杀伤链之间的双向数据交换，延迟 < 1 秒。

---

## 1. 背景与约束

- **实时性要求：** < 1 秒延迟
- **部署方式：** 同一台 Windows 机器
- **Python 杀伤链需要：** 目标航迹、识别结果、系统状态（传感器/武器/网络）、发出控制指令
- **核心问题：** DIS interface 有 bug（崩溃），XIO 是 WSF 内部协议无法直接接入

---

## 2. 架构概述

```
┌─────────────────────────────────────────────────────────────┐
│                      AFSIM 进程                              │
│  ┌──────────────────┐    ┌──────────────────────────────┐  │
│  │  wkf_track_writer │───▶│  Memory-Mapped File (SHM)    │  │
│  │  (C++ 插件)       │    │  kill_chain_shm.dat          │  │
│  │                   │    │                              │  │
│  │  - 写航迹/状态     │    │  [TrackEntry[], CmdEntry]    │  │
│  │  - 读指令         │    │                              │  │
│  └──────────────────┘    └──────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                                    ▲
                                    │ read
                                    │
┌─────────────────────────────────────────────────────────────┐
│                   Python 杀伤链进程                          │
│  ┌──────────────────┐    ┌──────────────────────────────┐  │
│  │  shm_client.py   │───▶│  同上 Memory-Mapped File     │  │
│  │                   │    │                              │  │
│  │  - 读航迹/状态     │    │  - 读: tracks[]             │  │
│  │  - 写指令         │    │  - 写: commands[]            │  │
│  └──────────────────┘    └──────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. 共享内存数据结构

### 3.1 文件格式

- **文件名：** `kill_chain_shm.dat`
- **大小：** 64 MB（固定，预留足够空间）
- **格式：** Memory-mapped file，Python 和 C++ 共用同一块内存

### 3.2 布局

```
[Header]         128 bytes   — 版本号、状态、时间戳
[TrackArray]     64 KB       — 最多 512 个航迹 (128 bytes/entry)
[SensorArray]    16 KB       — 最多 256 个传感器状态 (64 bytes/entry)
[WeaponArray]    16 KB       — 最多 256 个武器状态 (64 bytes/entry)
[CmdArray]       32 KB       — 最多 256 条未处理指令 (128 bytes/entry)
[CmdAckArray]    16 KB       — 最多 256 条指令回执 (64 bytes/entry)
[Fence]          8 bytes     — MMF 围栏标记
```

### 3.3 数据类型定义

```cpp
// ===== 枚举 =====

enum class TargetType : uint8_t {
    AIRCRAFT = 0,
    MISSILE = 1,
    UCAV = 2,
    JAMMER = 3,
    UNKNOWN = 255
};

enum class SensorMode : uint8_t {
    OFF = 0,
    STANDBY = 1,
    SEARCH = 2,
    TRACK = 3,
    JAMMING = 4
};

enum class WeaponStatus : uint8_t {
    READY = 0,
    LAUNCHED = 1,
    INTERCEPTING = 2,
    DEPLETED = 3
};

enum class CmdType : uint8_t {
    NONE = 0,
    SENSOR_CONTROL = 1,    // 传感器开关/模式
    WEAPON_ASSIGN = 2,     // 武器分配拦截
    TARGET_PRIORITY = 3,   // 目标优先级
    PLATFORM_MOVE = 4      // 平台移动指令
};

// ===== 主结构 =====

struct ShmHeader {
    uint32_t magic;            // 0x4B494C4C ("KILL")
    uint16_t version;           // 1
    uint16_t track_count;       // 当前航迹数
    uint32_t timestamp_ms;      // 最新更新时间
    uint32_t cmd_in;            // 下一条待处理指令索引
    uint32_t cmd_out;           // 下一条已确认指令索引
    uint8_t  afsim_ready;       // AFSIM 已初始化
    uint8_t  padding[7];
    uint64_t fence;             // 0xDEADBEEFDEADBEEF
};

struct TrackEntry {
    uint32_t track_id;          // 航迹号
    double   lat;               // 纬度 (deg)
    double   lon;               // 经度 (deg)
    double   altitude;           // 高度 (m MSL)
    double   velocity;          // 速度 (m/s)
    double   heading;           // 航向 (deg, 0-360)
    double   timestamp_ms;      // 时间戳
    TargetType type;            // 目标类型
    uint8_t  force;             // 0=friend, 1=hostile, 2=neutral
    uint8_t  track_quality;     // 0-100
    uint16_t padding;
};

struct SensorEntry {
    uint32_t sensor_id;         // 传感器 ID
    char     name[24];          // 名称
    double   lat;               // 传感器位置
    double   lon;
    double   altitude;
    SensorMode mode;           // 当前模式
    uint8_t  side;              // 0=red, 1=blue, 2=neutral
    uint8_t  padding[7];
    double   timestamp_ms;
};

struct WeaponEntry {
    uint32_t weapon_id;
    char     name[24];
    uint32_t platform_id;       // 所属平台
    double   lat;
    double   lon;
    double   altitude;
    WeaponStatus status;        // 当前状态
    uint8_t  side;
    uint8_t  padding[7];
    double   timestamp_ms;
};

struct CmdEntry {
    uint32_t cmd_id;            // 命令序列号
    CmdType  type;              // 命令类型
    uint32_t sender_id;         // 发送方 (0=Python)
    uint32_t target_id;         // 目标实体 ID
    uint32_t param1;            // 参数1 (传感器ID/武器ID等)
    uint32_t param2;            // 参数2
    double   param3;            // 浮点参数 (优先级等)
    uint8_t  acknowledged;     // 0=pending, 1=acked
    uint8_t  padding[7];
    uint32_t timestamp_ms;      // 发送时间
};
```

---

## 4. 双方向数据流

### 4.1 AFSIM → Python（读取态势）

**触发条件：** `mover_update_timer` 或每 1 秒强制刷新（配置 `mover_update_timer 1.0 sec`）

**写入内容：**
- 所有活跃航迹（来自 WSF_TRACK_PROCESSOR）
- 所有传感器当前模式（on/off/search/track）
- 所有武器当前状态（ready/launched/depleted）

**Python 读取：** 轮询 + 事件通知（用 `mmap` 配合文件变更通知）

### 4.2 Python → AFSIM（发送指令）

**指令队列流程：**

```
Python 写 cmd_in → AFSIM 轮询 cmd_in → 执行指令 → 写 cmd_ack
```

**指令处理延迟目标：** < 100ms

**详细指令：**

| 指令类型 | param1 | param2 | param3 |
|---|---|---|---|
| SENSOR_CONTROL | sensor_id | mode (0-4) | - |
| WEAPON_ASSIGN | weapon_id | track_id | priority |
| TARGET_PRIORITY | track_id | - | priority (0-100) |
| PLATFORM_MOVE | platform_id | - | heading (deg) |

---

## 5. AFSIM 插件实现

### 5.1 插件位置

```
D:\afsim-2.9.0-win64\bin\wkf_plugins\wkf_track_writer.dll
```

### 5.2 依赖

- `wsf.dll` — AFSIM 核心库
- `wkf.dll` — 工作流插件框架
- `ShmWriter.h` — 自定义，写入共享内存

### 5.3 读取 AFSIM 内部数据的方式

由于无法直接访问 DIS/XIO，通过以下方式获取数据：

1. **航迹：** 使用 AFSIM 脚本输出（`writeln` 到文件），Python 监控文件变化写入共享内存
2. **传感器/武器状态：** 通过 WSF 脚本遍历 `PLATFORM.Subordinates()` 的 sensor 和 weapon 对象状态

**备选方案（如果脚本不够用）：**
扩展现有 wkf 插件框架，在 C++ 层直接读取 WSF 对象树并写入共享内存。

---

## 6. Python 侧实现

### 6.1 依赖模块

```python
# src/core/shared_mem/shm_client.py
import mmap
import struct
import ctypes
from pathlib import Path

# 现有 shm_types.h 对应 Python 版本
# TrackEntry, CmdEntry 等用 ctypes.Structure 定义
```

### 6.2 读取循环

```python
# 伪代码
while running:
    header = shm.read_header()
    if header.magic != 0x4B494C4C:
        continue  # 无效
    for i in range(header.track_count):
        track = shm.read_track(i)
        milp_allocator.process_track(track)
    process_commands()  # 检查指令回执
    time.sleep(0.01)  # 10ms 轮询
```

---

## 7. 配置修改

### 7.1 AFSIM 场景配置

```cui
# kill_chain_scenario.txt
define_path_variable CASE kill_chain
log_file output/$(CASE).log

realtime

include D:\afsim-2.9.0-win64\demos\iads\setup.txt

# AFSIM 端：输出脚本到文件
include D:\afsim-2.9.0-win64\demos\iads\xio_interface.txt

# 强制 mover 更新频率 1 秒
dis_interface
   mover_update_timer 1.0 sec
   heartbeat_timer 1.0 sec
   suppress_non_standard_data true
end_dis_interface

# 雷达默认开机（探测开关）
include D:\afsim-2.9.0-win64\demos\iads\scenarios\iads_laydown.txt
include D:\afsim-2.9.0-win64\demos\iads\scenarios\strike.txt

end_time 10 min
```

### 7.2 Python 启动配置

```json
// config/shm_config.json
{
  "shm_name": "kill_chain_shm",
  "poll_interval_ms": 10,
  "afsim_exercise_id": 1
}
```

---

## 8. 测试计划

| 测试 | 验证内容 |
|---|---|
| T1 | AFSIM 能启动，写入共享内存（航迹存在） |
| T2 | Python 能读取共享内存，读到航迹数据 |
| T3 | Python 发送 SENSOR_CONTROL 指令，AFSIM 正确响应 |
| T4 | Python 发送 WEAPON_ASSIGN 指令，AFSIM 正确分配武器 |
| T5 | 端到端延迟 < 1 秒（timestamp 差分验证） |

---

## 9. 风险与备选方案

| 风险 | 缓解方案 |
|---|---|
| AFSIM 脚本无法输出 UDP/文件 | 退回到方案 A：监控 AFSIM 输出文件 |
| wkf_plugins C++ 编译困难 | 用 Python 文件监控代替 C++ 插件 |
| DIS interface 崩溃 | 只用 xio_interface + 文件监控，不开 dis_interface |

---

## 10. 下一步行动

1. **立即：** 编写 Python `ShmClient` 类，完成共享内存的读写封装
2. **并行：** 测试 AFSIM 脚本能否通过 `writeln` 输出航迹信息到文件
3. **后续：** 若脚本可行，开发 AFSIM C++ 插件；若不可行，用文件监控桥接