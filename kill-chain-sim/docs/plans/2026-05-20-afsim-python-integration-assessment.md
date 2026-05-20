# AFSIM→Python 实时仿真通道 — Kill Chain 进展评估 & 执行计划

**日期：** 2026-05-20  
**状态：** 进展评估 + 执行计划

---

## 一、当前系统全貌

```
AFSIM 进程 (mission.exe)
├── DIS/xio_interface → UDP multicast 235.7.11.27:3002
├── wsf_shm.dll        → 共享内存 wsf_shm.dll (Python ctypes 调用)
│   ├── wsf_shm_process_new_commands()    [AFSIM 读取 Python 命令]
│   └── wsf_shm_get_cmd_in / read_cmd()    [AFSIM 读命令队列]
├── wkf_track_writer   → 输出 TRACK: 到日志文件或 stdout
└── PLATFORM.MasterTrackList() → 航迹列表

Python 进程 (src/main.py KillChainManager)
├── DisClient         → UDP multicast 监听 Entity State/Fire/Detonation PDU
├── ShmClient         → memory-mapped file (kill_chain_shm.dat)
│   ├── 读：tracks[], sensors[], weapons[]
│   └── 写：commands[] + poll_command_ack()
├── MilpAllocator     → 目标分配
└── MetricsEvaluator → 杀伤链评估

文件通道（备用）：
├── kill_chain_track_writer.txt → TRACK: 输出到 stdout
└── afsim_bridge.py             → 读取 stdout TRACK: → 写 SHM
```

---

## 二、已验证 / 未验证清单

### ✅ 已验证（单元测试覆盖）

| 组件 | 状态 |
|------|------|
| DIS 协议解析 (Entity State/Fire/Detonation/Signal) | ✅ 43 tests |
| EntityTracker | ✅ 6 tests |
| FireControl | ✅ 5 tests |
| EsmClient + ESM Trajectory Tracker | ✅ 5+5 tests |
| DisClient (async multi-threaded) | ✅ 7 tests |
| ShmClient (共享内存读写) | ✅ 5 tests |
| Munkres / Greedy / MILP Allocator | ✅ 9 tests |
| MetricsEvaluator | ✅ 9 tests |
| TrackFileMonitor (AFSIM log → SHM) | ✅ 2 tests |
| **总计** | **107 tests pass** |

### ⚠️ 未端到端验证（集成断点）

| 断点 | 说明 |
|------|------|
| **AFSIM → Python DIS 接收** | DIS multicast 接收从未与真实 AFSIM 联调 |
| **AFSIM → Python SHM 读取** | wsf_shm.dll 在 AFSIM 侧只写了部分接口 |
| **Python → AFSIM SHM 命令写入** | wsf_shm.dll 存在但函数签名未知，kill_chain_cmd_reader.txt 未加载 |
| **Python → AFSIM DIS Fire PDU** | send_fire() 从未联调 |
| **AFSIM 场景航迹输出** | kill_chain_track_writer processor 未输出到 SHM，只输出到 log |
| **afsim_bridge.py** | 已实现但未与 AFSIM 实时联调 |

---

## 三、AFSIM→Python 实时仿真通道分析

### 通道 1：DIS multicast（推荐，延迟 < 100ms）

```
AFSIM dis_interface → UDP 235.7.11.27:3002
                          ↓
                    Python DisClient
                          ↓
                    EntityTracker
                          ↓
                    MilpAllocator
                          ↓
                    FireControl.send_fire()
                          ↓
                    DisClient.send_fire() → UDP multicast
                          ↓
                    AFSIM receives Fire PDU
```

**现状：**
- AFSIM 配置：dis_realtime.txt 或 xio_interface.txt（两者都启用了 multicast）
- Python DisClient 已完整实现，但从未与真实 AFSIM 对接
- `send_fire()` 从未端到端测试

**问题：** AFSIM 2.9.0 的 DIS interface 已知有 bug（崩溃），但 xio_interface 更稳定

### 通道 2：共享内存（最低延迟，< 10ms）

```
AFSIM wsf_shm.dll ← SHM file → Python ShmClient
AFSIM wkf_track_writer → stdout → afsim_bridge.py → SHM
AFSIM kill_chain_cmd_reader → reads commands → wsf_shm_process_new_commands()
```

**现状：**
- wsf_shm.dll 存在（126KB）
- kill_chain_cmd_reader.txt 存在但未集成到场景
- kill_chain_track_writer.txt 只写到日志，未写到共享内存
- afsim_bridge.py 读取 stdout 但从未实时运行

**问题：** wsf_shm.dll 的 C 函数签名未知，Python ctypes 调用可能不匹配

---

## 四、关键集成断点（按优先级）

### P0：DIS 端到端（最简单）

```
1. 启动 AFSIM kill_chain_iads.txt（带 DIS）
2. 启动 Python main.py
3. 验证 Entity State PDU → EntityTracker 收到航迹
4. 验证 allocation → Fire PDU 发送
5. 验证 AFSIM 接收 Fire 并发射拦截弹
```

**需要：**
- AFSIM 场景加上 `dis_interface` 配置
- 去掉 crash 的 dis_interface，改用 xio_interface + DIS fallback

### P1：SHM 命令写入验证

```
1. 用 dumpbin / exports 或 Python ctypes 自省 wsf_shm.dll
2. 确定 wsf_shm_process_new_commands() 等函数签名
3. 写 mock AFSIM：读取 SHM cmd 队列并模拟 ack
4. Python send_weapon_assign() → 验证写入 + ack 读取
```

### P2：AFSIM → Python SHM 航迹写入

```
1. 修改 kill_chain_track_writer.txt 输出到 stdout（已有 TRACK: 格式）
2. 运行 afsim_bridge.py 读取 TRACK: → ShmClient 写入 SHM
3. Python main.py 读取 SHM tracks[] 而非 DIS
```

---

## 五、推荐执行计划

### Option A：DIS 优先（最快出结果）

```
Step 1: 修复 AFSIM 场景 DIS 配置（去掉 crash 的 dis_interface）
Step 2: 运行 AFSIM + Python main.py，观察 Entity State PDU 接收
Step 3: 验证 MILP allocation 输出 Fire PDU
Step 4: 记录端到端延迟
```

### Option B：SHM 优先（最低延迟）

```
Step 1: 自省 wsf_shm.dll，确定 C 函数签名
Step 2: 写 Python → AFSIM SHM 命令通路（mock 测试）
Step 3: 集成 kill_chain_cmd_reader.txt 到 AFSIM 场景
Step 4: 运行 afsim_bridge.py + AFSIM + Python main.py
```

---

## 六、C++ 编译问题

**问题：** CMake 无法找到 MinGW Makefiles（`CMAKE_MXX_PROGRAM` 未设置）  
**影响：** C++ 的 shm_client.cpp / ucs_client.cpp 无法编译  
**现状：** 所有功能已用纯 Python (ctypes + mmap) 实现，C++ 层是可选优化  
**建议：** 暂不修，聚焦 Python 层验证

---

## 七、验收标准（2026-05-20 目标）

- [ ] AFSIM 运行 kill_chain_iads.txt，输出 DIS Entity State
- [ ] Python main.py 收到航迹，日志显示 EntityTracker 有实体
- [ ] MILP allocator 产生分配决策
- [ ] Fire PDU 发送到 AFSIM（DIS 或 SHM）
- [ ] 端到端延迟 < 5 秒（TRACK: 出现到 Fire 发出）
- [ ] 107 tests 持续通过