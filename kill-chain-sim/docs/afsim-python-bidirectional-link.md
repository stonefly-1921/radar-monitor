# AFSIM ↔ Python 双向链路 — 方案分析

> 创建时间：2026-05-22
> 目标：AFSIM 和 Python 双向跑通，支持反导/一对一空战简单场景

---

## 一、已尝试的方案（5条）

| # | 方案 | 结果 | 死因 |
|---|------|------|------|
| 1 | **MinGW 编译 C++ SDK 插件** | ❌ 失败 | AFSIM SDK 头文件依赖链太深，transitive include 几十个，手动补不完 |
| 2 | **MSVC 手动 cl.exe + include paths** | ❌ 失败 | 同上 + `UT_PLUGIN_API` 宏链导致 dllimport/dllexport 冲突 |
| 3 | **CMake 集成进 AFSIM SDK 构建** | ❌ 超时/卡住 | CMake generator 版本匹配问题（需要 VS2019，机器装的是 VS2022）|
| 4 | **SDK 预编译 wsf_shm.dll** | ✅ AFSIM能加载 | AFSIM→Python 方向通（stdout→bridge→SHM）；Python→AFSIM 方向不通（只注册了C函数，没有注册script-command）|
| 5 | **Named Pipe（DLL侧做client，Python侧做server）** | ✅ E2E PING/PONG验证通过，180s压力测试不崩 | Python→AFSIM 段断：pipe通了，但 AFSIM 内部没有注册 script-command object，发指令进来没有执行动作 |

---

## 二、往下走的4条路径

### 路径A：Named Pipe + 注册 script-command object
- 在 `WsfPluginSetup` 里调用 `aApplication.GetScriptTypes()->Register(...)` 注册脚本类
- WSF 脚本层可调用 `var cmd = new NamedPipeCommand(); cmd.Fire(weapon, target)`
- 需要 `UT_DECLARE_SCRIPT_METHOD` / `UT_DEFINE_SCRIPT_METHOD` 宏（SDK内部）
- **可行性**：中低 — 模式参考 wsf_air_combat，但宏定义缺失

### 路径B：文件轮询（锚定路径）✅
- Python 写 JSON 命令文件
- DLL per-frame `DoExecute()` 轮询文件，调用 `Fire()`
- 不需要 SDK 内部头文件，不依赖 script layer
- 延迟 10-50ms，可接受
- **可行性**：高

### 路径C：SDK 官方 wsf_shm CMake rebuild
- AFSIM 预装了 `BUILD/Release/wsf_plugins/wsf_shm.dll`
- 官方 wsf_shm 源码在 SDK，CMake 配置已写好
- 需要解决 CMake generator 版本匹配问题
- **可行性**：中

### 路径D：event_output .evt 文件触发
- AFSIM 写 event_output .evt 文件，Python 轮询读
- 不需要 DLL，纯事件驱动
- **可行性**：低 — 之前试过，没有和指令下发结合

---

## 三、当前锚定路径：路径B（文件轮询）

### 架构
```
Python (kill_chain_sim.py)
    ↓ writes JSON
Command File (C:/Users/15041/.openclaw/workspace/kill-chain-sim/kill_chain_cmd.json)
    ↑ polls every frame
DLL (wsf_named_pipe.dll 或新写的 wsf_file_poll.dll)
    ↓ calls Fire()
AFSIM (WsfTaskManager.Fire() built-in)
```

### Fire() 接口（从 SDK 源码已知）
```csharp
bool ok = Fire(WsfTrack aTrack, string aTaskType, string aWeaponName, int aQuantity, WsfPlatform aPlatform);
```
- `aTrack`：目标轨道，来自 `platform.MasterTrackList().Find(trackId)`
- `aWeaponName`：武器名称字符串
- `aPlatform`：武器所在平台，来自 `simulation.GetPlatform(platformName)`

---

## 四、文件位置参考

| 文件 | 路径 |
|------|------|
| 项目根目录 | `C:/Users/15041/.openclaw/workspace/kill-chain-sim/` |
| AFSIM bin | `D:/afsim-2.9.0-win64/bin/` |
| AFSIM plugins | `D:/afsim-2.9.0-win64/bin/wsf_plugins/` |
| AFSIM SDK | `D:/afsim-2.9.0-win64/swdev/` |
| 现有 DLL 源码 | `C:/Users/15041/.openclaw/workspace/kill-chain-sim/src/core/wsf_named_pipe/wsf_named_pipe.cpp` |
| 现有 Python 端 | `C:/Users/15041/.openclaw/workspace/kill-chain-sim/src/core/wsf_named_pipe/kill_chain_sim.py` |
| 场景文件 | `C:/Users/15041/.openclaw/workspace/kill-chain-sim/src/sim/kill_chain_*.txt` |
| 命令文件（Plan B 用） | `C:/Users/15041/.openclaw/workspace/kill-chain-sim/kill_chain_cmd.json` |

---

## 五、已知关键接口

### Fire() built-in（ANTI_BALLISTIC_MISSILE_PROCESSOR 参考）
```csharp
WsfWeapon weap = sub.Weapon(WEAPON_NAME);
bool Launched = Fire(LocalTrack, "FIRE", weap.Name(), 1, sub);
```
- 在 script processor 里，通过 `sub`（WsfSubsystem）获取 Weapon
- 从 `track.MasterTrackList().Find(trackId)` 获取 WsfTrack

### WsfPlatform 遍历（SDK 源码）
```cpp
for (size_t i = 0; i < simulationPtr->GetPlatformCount(); ++i) {
    WsfPlatform* platformPtr = simulationPtr->GetPlatformEntry(i);
}
```

### Track 获取
```cpp
WsfLocalTrackList& tracks = platformPtr->GetMasterTrackList();
for (unsigned int i = 0; i < tracks.GetTrackCount(); ++i) {
    WsfTrack* track = tracks.GetTrackEntry(i);
}
```
