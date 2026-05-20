# AFSIM-Python 双向通道架构设计

## 问题定义

在 AFSIM 仿真中实现 Python 与 AFSIM 的双向实时通信，延迟要求 < 50ms。

## 当前状态

### 已有组件
- `wsf_shm.c` — 纯 C 共享内存插件（DLL），MinGW 可编译
- `shm_client.py` — Python SHM 客户端，读写 `kill_chain_shm.dat`
- `afsim_bridge.py` — AFSIM stdout → Python 解析中转（当前实际数据流）

### 核心问题：两套 SHM 布局不兼容
```
Python shm_client.py 布局:
  [Header 128B][Tracks:512×72B][Sensors][Weapons][Cmds:256×44B][CmdAck]
  Magic: 0x4B494C4C

C wsf_shm.c 布局:
  [Header 128B][Tracks:256×64B][Cmds:256×128B]
  无 Magic（纯字段计数）
```
TrackEntry 大小不同（72 vs 64 字节），**无法互通**。

### 实时性分析

| 方向 | 方案 | 延迟 | 状态 |
|------|------|------|------|
| AFSIM→Python | stdout 解析 | ~5-20ms | 已通（afsim_bridge.py） |
| AFSIM→Python | DIS PDU | ~1-5ms | 可用（DIS 监听） |
| Python→AFSIM | WSF_SCRIPT_PROCESSOR | ≥100ms（最小 update_interval=0.1s） | 太慢 |
| Python→AFSIM | Native Plugin PrepareExtension | ~1ms per frame | **正确路径** |

## 推荐架构

### 核心：统一 SHM 布局 + Native Plugin

```
┌─────────────────────────────────────────────────────────┐
│  AFSIM Simulation (Native Plugin: wsf_shm.dll)          │
│                                                         │
│  Per-Frame (PrepareExtension):                          │
│    tracks[] ← PLATFORM.MasterTrackList()   (写 SHM)    │
│    cmds[]  ← poll SHM cmd queue           (读 SHM)     │
└─────────────────────────────────────────────────────────┘
              ↕ SHM (Global\kill_chain_shm)
┌─────────────────────────────────────────────────────────┐
│  Python (shm_client.py)                                 │
│                                                         │
│    tracks[] ← SHM        (读态势)                       │
│    cmds[]  → SHM        (写命令)                        │
│    kill_chain_manager.py — 杀伤链决策逻辑                │
└─────────────────────────────────────────────────────────┘
```

### SHM 布局（统一版，与 shm_client.py 兼容）

```
Offset 0x00000: [ShmHeader 128B]
  magic=0x4B494C4C, version=1, track_count, cmd_in, cmd_out, afsim_ready, fence
Offset 0x00080: [TrackEntry tracks[512]]
  track_id, lat, lon, altitude, velocity, heading, timestamp_ms, type, force, track_quality (72B each)
Offset 0x09080: [CmdEntry cmds[256]]
  cmd_id, type, sender_id, target_id, param1, param2, param3, description (44B each)
Total: 64KB
```

### Native Plugin 职责

1. **WsfPluginVersion/WsfPluginSetup** — DLL 加载入口
2. **WsfShmSimulationExtension::PrepareExtension** — 每帧执行：
   - `PLATFORM.MasterTrackList()` → 写入 SHM tracks
   - `cmd_in != cmd_out` → 读取新命令并处理
3. **WsfShmScenarioExtension::SimulationCreated** — 注册 SimulationExtension

### Python 端职责

1. **ShmClient** (已有) — 连接 SHM，读 tracks，写 cmds
2. **kill_chain_manager.py** — 决策逻辑：
   - 收到 track → 评估威胁 → 分配拦截资源
   - 写 cmd (SENSOR_CONTROL / WEAPON_ASSIGN / TARGET_PRIORITY)

### 编译要求

- **编译器**: conda-forge GCC 15.2.0 (`D:/anaconda3/Library/bin/gcc.exe`)
- **构建**: `gcc -shared -o wsf_shm.dll wsf_shm.c -DBUILD_DLL=1`
- **SDK 不需要** — 入口函数签名是公开 API

## 开发工作流

```
1. 编辑 wsf_shm.c (或新增 .hpp)
2. 运行 build_wsf_shm.bat
3. 测试:
   a. AFSIM: mission.exe -rt scenario.txt
   b. Python: python kill_chain_manager.py
4. 调试: 观察 D:/afsim-2.9.0-win64/output/ 下的日志
```

## 当前障碍

1. **C++ 插件编译** — 需要 MSVC 或修复 MinGW 链接
2. **SHM 布局统一** — 需要决定用哪套布局（建议：统一用 shm_client.py 的布局）
3. **WSF_SCRIPT_PROCESSOR 无法满足实时性** — 必须用 Native Plugin

## 下一步

1. 确认统一 SHM 布局（与用户确认）
2. 实现 Python → AFSIM 命令注入（先验证单方向）
3. 实现 AFSIM → Python 态势输出
