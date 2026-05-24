# AFSIM + Python 联合仿真操作步骤

## 环境信息

- AFSIM: `D:/afsim-2.9.0-win64/bin/mission.exe`
- 工作目录: `C:/Users/15041/.openclaw/workspace/kill-chain-sim`
- 场景文件: `src/sim/kill_chain_np_multi.txt`
- EVT输出: `output/kill_chain_np_multi.evt`
- Track输出: `afsim_track_out.txt`
- 命令文件: `kill_chain_np_cmd.txt` / `kill_chain_np_ack.txt`

---

## Step 0: 检查 wsf_shm.dll 是否需要重新编译

**何时需要:** AFSIM 报错 `Unable to find WsfPluginVersion symbol`

**检查方法:**
```bash
cd /c/Users/15041/.openclaw/workspace/kill-chain-sim
strings D:/afsim-2.9.0-win64/bin/wsf_plugins/wsf_shm.dll | grep WsfPlugin
```
若有输出 `WsfPluginVersion` 和 `WsfPluginSetup` → OK，跳过 Step 1
若无输出 → 执行 Step 1

---

## Step 1: 重新编译 wsf_shm.dll（仅在需要时）

```bash
cd /c/Users/15041/.openclaw/workspace/kill-chain-sim
CC=D:/anaconda3/Library/bin/gcc.exe
$CC -shared -o D:/afsim-2.9.0-win64/bin/wsf_plugins/wsf_shm.dll \
   src/wsf_shm/wsf_shm.c -DBUILD_DLL=1
```

**验证:**
```bash
strings D:/afsim-2.9.0-win64/bin/wsf_plugins/wsf_shm.dll | grep WsfPlugin
# 期望输出: WsfPluginVersion \n WsfPluginSetup
```

---

## Step 2: 清理旧文件

```bash
cd /c/Users/15041/.openclaw/workspace/kill-chain-sim
rm -f afsim_track_out.txt kill_chain_np_cmd.txt kill_chain_np_ack.txt
# 可选：清空 EVT
# rm -f output/kill_chain_np_multi.evt
```

---

## Step 3: 启动 AFSIM 仿真（后台）

```bash
cd /c/Users/15041/.openclaw/workspace/kill-chain-sim
D:/afsim-2.9.0-win64/bin/mission.exe src/sim/kill_chain_np_multi.txt 2>&1
```

**重要:**
- 工作目录必须是 `C:/Users/15041/.openclaw/workspace/kill-chain-sim`（KILL_CHAIN_DIR）
- 不要加 `--scenario` 参数，直接用相对路径
- 用 `background=true` 在 terminal 里跑，方便后续检查

---

## Step 4: 等待 AFSIM 初始化（3-5秒）

AFSIM 启动后输出 `SENSOR_CTRL: radar1 -> ON (active)` 表示雷达开启成功

---

## Step 5: 启动 Python Fire Controller

```bash
cd /c/Users/15041/.openclaw/workspace/kill-chain-sim
python src/tools/kill_chain_np_fire_controller.py --scenario src/sim/kill_chain_np_multi.txt
```

**参数说明:**
- `--scenario` 后的路径是相对于 KILL_CHAIN_DIR 的场景文件路径
- 必须在 KILL_CHAIN_DIR 下运行
- Fire controller 会轮询 `afsim_track_out.txt`，读取 track 数据并发送 FIRE 命令

---

## Step 6: 监控仿真状态

### 6a. 检查 track 数据（AFSIM→Python）
```bash
cat /c/Users/15041/.openclaw/workspace/kill-chain-sim/afsim_track_out.txt
```
期望输出类似:
```
TRACK_COUNT: 5 time=60.0
TRACK: id=2 lat=38.0917 lon=-117.233 alt=500 vel=300 hdg=180
...
```

### 6b. 检查 FIRE 命令（Python→AFSIM）
```bash
cat /c/Users/15041/.openclaw/workspace/kill-chain-sim/kill_chain_np_cmd.txt
```
期望输出类似:
```
FIRE:aim120_sim_1:radar1:2
FIRE:aim120_sim_2:radar1:4
```

### 6c. 检查 ACK（AFSIM→Python）
```bash
cat /c/Users/15041/.openclaw/workspace/kill-chain-sim/kill_chain_np_ack.txt
```
期望: `ACK`

### 6d. 检查 EVT 文件
```bash
cat /c/Users/15041/.openclaw/workspace/kill-chain-sim/output/kill_chain_np_multi.evt
```
期望: 包含 `WEAPON_FIRED`、`WEAPON_HIT` 或 `WEAPON_MISSED`

---

## Step 7: 等待仿真结束

仿真时长 120s（`end_time 2 min`）。可通过日志确认：
```bash
cat /c/Users/15041/.openclaw/workspace/kill-chain-sim/output/kill_chain_np_multi.log
# 期望最后一行: "complete 120.001 ..."
```

---

## 已知问题 & 排查

### Q: AFSIM 报错 `Unable to find WsfPluginVersion symbol`
**A:** wsf_shm.dll 用错编译器编译了。执行 Step 1 重新编译。

### Q: track_out 里所有 vel=0
**A:** 这是 GeometricSensor 的 velocity 报告配置问题（AFSIM 已知行为），不影响 FIRE 命令发送。fire_controller 用 distance 做主要排序依据。

### Q: cmd.txt 为空，Python 没发 FIRE 命令
**A:** 检查 `afsim_track_out.txt` 是否有 track 数据。若无 track，说明 AFSIM 雷达未检测到目标（可能目标还未进入场景）。

### Q: AFSIM 立即退出（exit code 1）
**A:** 检查 `mission-exception.log` 或场景 .log 文件，查找 `*** ERROR` 或 `FATAL`。

---

## 上次运行结果（2026-05-24 验证成功）

```
WEAPON_FIRED=4, WEAPON_HIT=3, WEAPON_MISSED=1, WEAPON_TERMINATED=4
拦截率 = 75%（3/4）
```

**关键修复记录：**
1. wsf_shm.dll 重新用 GCC 编译后导出 `WsfPluginVersion` + `WsfPluginSetup`
2. kill_chain_np_cmd_reader.txt 的 `targetTrack.TargetPlatform().IsValid()` → `targetTrack.IsValid()`
3. fire_controller.py 的 vel=500 边界 `>` → `>=`
4. fire_controller.py 的 vel=0 预警机 threat floor + 分类升级

| 文件 | 方向 | 作用 |
|------|------|------|
| `afsim_track_out.txt` | AFSIM → Python | 每 100ms 写出当前 track 列表 |
| `kill_chain_np_cmd.txt` | Python → AFSIM | Python 写入 FIRE/SENSOR 命令 |
| `kill_chain_np_ack.txt` | AFSIM → Python | cmd_reader 处理完写 ACK |
| `output/kill_chain_np_multi.evt` | AFSIM → 文件 | 事件记录（FIRE/HIT/MISS） |