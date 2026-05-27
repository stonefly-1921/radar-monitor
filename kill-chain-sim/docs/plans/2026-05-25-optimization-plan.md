# kill-chain-sim 优化计划（2026-05-25）

## 现状

### 当前版本的问题

**根本原因：我今天重写了 `kill_chain_np_multi.txt`，但破坏了关键语法：**

| 问题 | 原因 |
|------|------|
| ASM/Fighter 目标 speed=0 | 移除了 `mover WSF_AIR_MOVER { maximum_speed }` |
| 目标静止不动 | 移除了 `creation_time`（分时段进入战场） |
| 目标从固定位置出现 | 移除了 `use_route`（战机沿航线移动） |
| FIGHTER_TARGET 是静止"飞机" | 用自定义 platform_type 替代了 `BLUE_ADV_FIGHTER_1_BASE` |
| 场景加载报错（speed/velocity） | 在 platform_type 内用了 `speed`/`velocity` 关键字（AFSIM 不支持） |

### 备份版本 vs 当前版本对比

**备份版本（2026-05-25 03:00, git 219716f）✅ 正常：**
- ASM_TARGET 有 `mover WSF_AIR_MOVER { maximum_speed 300 m/s }`
- Fighter 用 `BLUE_ADV_FIGHTER_1_BASE` + `use_route` 航线
- 目标有 `creation_time` 分时进入
- 曾达到 60% 拦截率（3/5 击杀）

**当前版本（刚破坏的）❌ 异常：**
- platform_type 没有 mover → 目标 speed=0
- platform 没有 route/creation_time → 目标静止
- 拦截率 0%（ASM 都 MISSED）

---

## 优化目标

1. **恢复正确的目标运动** — 使用备份版本的 mover/route/creation_time
2. **提高拦截率** — 分析为什么 ASM MISSED（射程？拦截几何？）
3. **消除决策延迟** — OODA avg=1970ms 过高高
4. **修复重复 FIRE bug** — 8 次发射但只 2 发有效

---

## 修复步骤

### Step 1: 恢复场景文件（从 git 备份）
从 git commit `219716f` 恢复 `kill_chain_np_multi.txt`，只修复必要的语法错误，不重新设计。

### Step 2: 验证场景加载
- AFSIM 无 FATAL error
- EVT 文件有 WEAPON 事件
- 目标有非零速度

### Step 3: 运行完整仿真 + Python controller
- 拦截率 > 50%
- OODA 延迟 < 500ms avg

### Step 4: 分析 MISSED 根因
- 如果 intercept probability = 0：射程不足或拦截几何差
- 检查 aim120_sim 射程参数
- 检查目标进入角度

---

## 关键文件

- `src/sim/kill_chain_np_multi.txt` — 场景定义
- `src/tools/kill_chain_np_fire_controller.py` — Python 控制器
- `output/fire_controller_run12.log` — 最近一次运行日志（拦截率 0%）