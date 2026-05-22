# 多目标杀伤链场景扩展 - 设计文档

## 1. 场景配置

### 1.1 目标配置（ABC 渐进式）

**A. 渐进式（基础验证）**
- target_A1~A4：4个战机目标，不同距离、不同进入角度
- 速度：300~500 m/s
- 高度：3000~8000 m
- 初始位置：从雷达射程边缘从不同方向接近

**B. 分层威胁**
- target_B1~B2：2枚反舰导弹，低空（500m），高速（600 m/s）
- target_B3~B4：2架战机，中空（5000m），中速（400 m/s）

**C. 饱和攻击**
- 总计6个目标同时进入
- 4枚拦截弹（无余量，精确资源分配）

### 1.2 红方配置

**雷达（传感器资源）**
- radar1：主战雷达，多模式
  - 搜索模式（默认）：全向搜索，低数据率（2s/帧）
  - 跟踪模式：指定目标跟踪，高数据率（0.25s/帧）
  - 照射模式：半主动制导

**武器资源**
- aim120_sim × 4（数量固定）
- 射程：约 30km（对应 aim120_sim 性能）
- 装填时间：不考虑（不可再装填）

### 1.3 场景文件

- 场景名：`kill_chain_np_multi.txt`
- 端时间：5 min（或更短以加快测试）

## 2. 系统架构

### 2.1 数据流

```
AFSIM (kill_chain_np_multi.txt)
  ├── radar1 (sensor) → 检测目标 → track_list
  ├── track_writer → 每 100ms 写 afsim_track_out.txt
  ├── sensor_controller (WSF_SCRIPT_PROCESSOR) ← 读 sensor_cmd.txt
  ├── cmd_reader (KILL_CHAIN_CMD_READER) ← 读 kill_chain_np_cmd.txt
  └── event_output → kill_chain_np_multi.evt (WEAPON_FIRED/HIT/MISSED)

Python (kill_chain_np_fire_controller.py)
  ├── 轮询 afsim_track_out.txt → 解析 track
  ├── 威胁评估 + 资源分配决策
  ├── 写 sensor_cmd.txt → 控制雷达模式/跟踪目标
  └── 写 kill_chain_np_cmd.txt → FIRE 命令
```

### 2.2 扩展命令格式

**FIRE 命令（现有）：**
```
FIRE:weapon_name:radar_name:track_num
例：FIRE:aim120_sim:radar1:2
```

**SENSOR_CONTROL 命令（新增）：**
```
SENSOR:radar_name:mode:track_name:track_num
例：SENSOR:radar1:TRACK:radar1:2    # 切换到跟踪模式，跟踪 radar1 的 track 2
SENSOR:radar1:SEARCH               # 切回搜索模式
SENSOR:radar1:HIGH_RATE             # 提高数据率
```

**批量命令格式：**
支持多命令换行分隔，Python 每次写完整决策结果，AFSIM 每次 on_update 读取。

## 3. Python 决策逻辑

### 3.1 数据结构

**Track（来自 afsim_track_out.txt）：**
```
TRACK: id=X lat=Y lon=Z alt=A vel=S hdg=H
```

**可用武器（hardcoded / 来自 AFSIM）：**
```
weapons = [
    {"name": "aim120_sim", "available": 4, "range_max": 30000, "reload_time": 0}
]
```

**传感器模式（hardcoded）：**
```
sensor_modes = {
    "SEARCH": {"data_rate": 2.0, "track": None},
    "TRACK": {"data_rate": 0.25, "track": <track_id>},
    "ILLUMINATE": {"data_rate": 0.25, "track": <track_id>}
}
```

### 3.2 威胁评估

**威胁指数计算：**
```
threat = distance_weight * (1/distance) + speed_weight * speed + type_weight * type_factor

type_factor:
  - 反舰导弹（ASM）：1.0
  - 战机（fighter）：0.7
  - 无人机（UAV）：0.5
```

**传感器覆盖判断：**
```
if 目标在雷达射程内 and 雷达当前模式能跟踪该目标:
    可以交战
```

### 3.3 资源分配（饱和判断）

**输入：**
- 威胁目标列表（按威胁指数排序）
- 可用武器列表

**分配算法：**
```
1. 过滤：去掉不在射程内的目标
2. 贪心分配：按威胁指数从高到低，每个目标分配1发武器
3. 饱和判断：if 可用武器数 < 待拦截目标数 → 选择最高优先级目标
4. 输出：FIRE 决策 + SENSOR 控制决策
```

### 3.4 传感器控制决策

**跟踪管理：**
```
if 有新目标进入雷达射程:
    if 雷达当前模式 != TRACK:
        下发 SENSOR:radar1:TRACK:radar1:<track_id>
    elif 当前跟踪目标威胁太低:
        下发 SENSOR:radar1:TRACK:radar1:<new_track_id>

if 所有目标均已拦截/丢失:
    下发 SENSOR:radar1:SEARCH
```

**数据率控制：**
```
if 目标数量 >= 3:
    下发 SENSOR:radar1:HIGH_RATE
```

## 4. AFSIM 扩展

### 4.1 传感器控制器 processor

```wsf
processor sensor_controller WSF_SCRIPT_PROCESSOR
   script_variables
      string mLastCmd = "";
      FileIO mCmdFile = FileIO();
   end_script_variables

   on_update
      string cmdPath = "C:/Users/15041/.openclaw/workspace/kill-chain-sim/sensor_cmd.txt";
      if (mCmdFile.Open(cmdPath))
      {
         string line = mCmdFile.Readln();
         mCmdFile.Close();

         if (line.Length() > 0 && line != mLastCmd)
         {
            Array<string> parts = line.Split(":");
            if (parts.Size() >= 2)
            {
               string action = parts[0].Strip();
               if (action == "SENSOR")
               {
                  string radarName = parts[1].Strip();
                  string mode = parts[2].Strip();
                  // 实现模式切换逻辑
                  writeln("SENSOR_CTRL: ", radarName, " -> ", mode);
               }
            }
            mLastCmd = line;
         }
      }
   end_on_update
end_processor
```

### 4.2 cmd_reader 扩展

扩展现有 `kill_chain_np_cmd_reader.txt`，解析 SENSOR 命令（但由 sensor_controller 执行，SENSOR 命令只是日志记录，实际控制通过 AFSIM 内部机制）。

## 5. 输出设计

### 5.1 事件日志（.evt）

AFSIM event_output 记录：
- WEAPON_FIRED
- WEAPON_HIT / WEAPON_MISSED
- 目标状态变化（可通过扩展获取）

### 5.2 Python 决策日志

```
[DECISION] t=12.5 | tracks=4 | weapons=4 available
  track 3 (ASM, d=25km, v=600) -> threat=0.92 -> FIRE:aim120_sim:radar1:3
  track 1 (fighter, d=30km, v=400) -> threat=0.71
  track 2 (fighter, d=35km, v=350) -> threat=0.60
  track 4 (UAV, d=40km, v=200) -> threat=0.40
  sensors: HIGH_RATE (4 tracks)
[RESULT] FIRE:aim120_sim:radar1:3 -> fired=True
```

### 5.3 统计摘要

```
=== 杀伤链统计 ===
场景时长：180s
目标总数：6
  - 反舰导弹：2
  - 战机：4

拦截结果：
  - 发射拦截弹：4
  - 命中：3
  - 漏网：3
  - 拦截率：75%

漏网目标：
  - target_B2 (ASM, d=18km时被拦截)
  - target_A3 (fighter, 未拦截)
  - target_A4 (fighter, 未拦截)

武器消耗：4/4
决策耗时：min=2ms max=15ms avg=5ms
```

## 6. 文件清单

### 新增文件
- `src/sim/kill_chain_np_multi.txt` — 多目标场景
- `src/tools/kill_chain_np_fire_controller.py` — Python 决策控制器

### 修改文件
- `src/sim/kill_chain_np_cmd_reader.txt` — 扩展支持 SENSOR 命令（仅解析，不执行）
- `src/sim/processors/sensor_controller.txt` — 新增传感器控制 processor
- `src/sim/kill_chain_np.txt` — 基础场景保留（单目标验证用）

## 7. 实现计划

### Task 1：场景文件
- 创建 `kill_chain_np_multi.txt`（6个移动目标，不同类型）
- 配置 event_output

### Task 2：AFSIM 扩展
- 创建 `sensor_controller.txt` processor
- 扩展 cmd_reader 解析 SENSOR 命令

### Task 3：Python 决策逻辑
- 实现威胁评估
- 实现资源分配（饱和判断）
- 实现传感器控制决策
- 实现统计摘要输出

### Task 4：集成测试
- 跑 3 分钟场景
- 验证命中评估
- 验证决策日志输出

## 8. 约束与限制

- 传感器控制为**仿真验证目的**（通过文件命令模拟控制，实际雷达行为由 AFSIM 内部逻辑决定）
- 不考虑电子对抗（EA）干扰（留待后续）
- 武器不可再装填
- 不考虑目标航路捷径（straight flight only）
