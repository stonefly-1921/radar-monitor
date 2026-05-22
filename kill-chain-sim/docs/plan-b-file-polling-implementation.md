# Plan B 实现计划：文件轮询 + WSF Script Processor

> 创建时间：2026-05-22
> 更新：2026-05-22（重大简化 — FileIO class + string.Split() 使 WSF 层全链路可行）

---

## 一、架构（最终版）

```
Python (kill_chain_sim.py)
    ↓ writes "FIRE:AA_01:5\n" 到文件
Command File (kill_chain_np_cmd.txt)
    ↑ 每帧轮询
WSF Script Processor (KILL_CHAIN_CMD_READER)
    ↓ 解析字符串，调用 Fire()
AFSIM (built-in Fire() function)
```

**关键发现**：
1. WSF 脚本有 `FileIO` class — 可直接读文件
2. WSF 脚本有 `string.Split(":")` — 直接解析 "FIRE:AA_01:5"
3. WSF 脚本有 `WsfTrackId.SetNumber(int)` — 直接从 int 构造 track ID
4. `Fire()` 是 WSF processor 里的 built-in，可直接调用
5. DLL 只负责 AFSIM→Python 方向（已有 stdout→bridge→SHM），Python→AFSIM 方向不需要 DLL 改动

**架构优势**：完全绕过 SDK 内部头文件、script-command 注册、JSON parser。纯 WSF 脚本 + 文件 IO。

---

## 二、命令文件格式

```
FIRE:weapon_name:track_id
```

例：
```
FIRE:AA_01:5
```

无多余格式，纯文本行，简单的 `file.Readln()` + `string.Split(":")` 解析。

---

## 三、任务分解

### Task 1：写 WSF Script Processor（KILL_CHAIN_CMD_READER）
**文件**：`src/sim/processors/kill_chain_np_cmd_reader.txt`

```csharp
processor KILL_CHAIN_CMD_READER WSF_SCRIPT_PROCESSOR
   update_interval 1.0 sec   // 每秒轮询
   script_variables
      string mLastLine = "";
   end_script_variables

   on_update
      // 打开命令文件
      FileIO cmdFile;
      if (cmdFile.Open("C:/Users/15041/.openclaw/workspace/kill-chain-sim/kill_chain_np_cmd.txt"))
      {
         string line = cmdFile.Readln();
         cmdFile.Close();

         if (line.Length() > 0 && line != mLastLine)
         {
            writeln("KCMD: received: ", line);
            mLastLine = line;

            // 解析 FIRE:weapon:track_id
            Array<string> parts = line.Split(":");
            if (parts.Size() >= 3)
            {
               string action = parts[0].Strip();
               string weaponName = parts[1].Strip();
               string trackNumStr = parts[2].Strip();
               int trackNum = (int)trackNumStr;

               if (action == "FIRE")
               {
                  // 构造 WsfTrackId 并查找 track
                  WsfTrackId tid;
                  tid.SetNumber(trackNum);
                  WsfLocalTrack targetTrack = PLATFORM.MasterTrackList().Find(tid);

                  if (targetTrack.IsValid())
                  {
                     WsfWeapon weap = PLATFORM.Weapon(weaponName);
                     if (weap.IsValid())
                     {
                        bool fired = Fire(targetTrack, "FIRE", weaponName, 1, PLATFORM);
                        writeln("KCMD: Fire ", weaponName, " at track ", trackNum,
                                " -> ", fired ? "LAUNCHED" : "FAILED");
                     }
                     else
                     {
                        writeln("KCMD: weapon not found: ", weaponName);
                     }
                  }
                  else
                  {
                     writeln("KCMD: track not found: ", trackNum);
                  }
               }
            }
         }
      }
   end_on_update
end_processor
```

**验证**：编译通过，AFSIM 加载后 scenario 里有这个 processor。

---

### Task 2：更新 scenario（kill_chain_engagement.txt 或新建）
**目标**：在有武器的平台挂载 KILL_CHAIN_CMD_READER processor

在 `platform blue_fighter` 里添加：
```
processor kill_chain_reader KILL_CHAIN_CMD_READER
end_processor
```

场景设置：
- 1个 blue fighter，武器名 `AA_01`
- 1个 red incoming missile（在雷达上产生 track）
- AFSIM 运行后，Python 端检测 track，下发 FIRE 命令

---

### Task 3：Python 端改动
**文件**：`src/core/wsf_named_pipe/kill_chain_sim.py`

在 AFSIM→Python 收到 track 之后、MILP 算完之后，追加一行：
```python
# 写 FIRE 命令到文件
cmd_file = "C:/Users/15041/.openclaw/workspace/kill-chain-sim/kill_chain_np_cmd.txt"
with open(cmd_file, 'w') as f:
    f.write(f"FIRE:{weapon_name}:{track_id}\n")
```

**注意**：Python 写文件不需要 admin 权限（不在 Global\ 命名空间），普通文件路径即可。

---

### Task 4：端到端测试
**场景**：反导（1v1，1个拦截弹 vs 1个 incoming missile）

**步骤**：
1. 启动 AFSIM：`D:/afsim-2.9.0-win64/bin/mission.exe ...`
2. Python 端跑 `kill_chain_sim.py`
3. AFSIM stdout 出现 missile track
4. Python 检测到 track → 写 "FIRE:AA_01:5\n" 到文件
5. WSF processor 读到 → 调用 Fire()
6. AFSIM stdout 显示武器发射事件
7. missile 被拦截（或拦截弹飞过没撞上）

**验证标志**：
- `kill_chain_np_cmd.txt` 有内容
- AFSIM log 有 "KCMD: received: FIRE:AA_01:5"
- AFSIM log 有 "KCMD: Fire AA_01 at track 5 -> LAUNCHED" 或 "FAILED"

---

## 四、TDD 循环

| 任务 | 测试 | 成功标准 |
|------|------|---------|
| Task 1 | AFSIM 加载 scenario，processor 不报语法错误 | "KCMD: received:" 出现在 stdout |
| Task 2 | 在 blue_fighter 上挂载 processor，AFSIM 运行不崩 | processor 正常初始化 |
| Task 3 | kill_chain_np_cmd.txt 被创建和写入 | 文件存在且内容格式正确 |
| Task 4 | 端到端 | 拦截弹发射（肉眼观察或 stdout 判断）|

---

## 五、文件改动清单

| 文件 | 操作 |
|------|------|
| `src/sim/processors/kill_chain_np_cmd_reader.txt` | 新建 |
| `src/sim/kill_chain_engagement.txt` | 修改：添加 processor |
| `src/core/wsf_named_pipe/kill_chain_sim.py` | 修改：写 FIRE 命令到文件 |
| `docs/afsim-python-bidirectional-link.md` | 更新架构图 |

---

## 六、风险点

| 风险 | 缓解 |
|------|------|
| `FileIO` class 在 AFSIM 2.9.0 里是否存在 | 已通过 `fileio.rst` 文档确认存在 |
| WSF 脚本 `int trackNum = (int)trackNumStr` 类型转换 | WSF string 支持 `(int)` cast |
| Python 和 AFSIM 并发写同一文件 | Python 写完立即退出（一次性写入），AFSIM 只读 |
| track_id 是 Python 端的 track 顺序号，和 AFSIM 内部的 track number 是否对应 | 需要确认 AFSIM stdout→bridge 的 track 信息里包含 track number |

---

## 七、下一步

**立即开始 Task 1**：写 `kill_chain_np_cmd_reader.txt`
