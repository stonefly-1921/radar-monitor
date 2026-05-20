# Kill Chain Sprint 计划

**目标：** 推动项目从"可运行"到"可演示"状态

---

## 第一步：修 Bug

**文件：** `tests/unit/test_shm_client.py::test_command_queue`

**问题：** `cmd_in` 计数异常，预期 1 实际 3

**原因分析：**
- `test_multiple_tracks` 和 `test_weapon_assign_command` 也在操作同一个 shm 文件
- pytest 没有隔离测试环境，header 被污染
- 需要 `conftest.py` 清理 fixture 或每个测试用独立 shm 文件

**修复方案：**
1. 检查 `conftest.py` 是否存在 shm 清理 fixture
2. 在 `test_command_queue` 开始时重置 shm header
3. 或者改用临时文件路径

---

## 第二步：完善共享内存联调

**目标：** 验证 Python → AFSIM 双向通信

**任务：**
1. 写 `src/sim/processors/kill_chain_track_writer.txt` — AFSIM processor 输出航迹到文件
2. 写 `src/core/shared_mem/track_file_monitor.py` — 监控文件写入共享内存
3. 验证 AFSIM 能接收来自 Python 的 weapon assign 命令

---

## 第三步：完善 DIS 联调

**目标：** 端到端验证 OODA 循环

**任务：**
1. 简化 `main.py` 的 allocation 逻辑，添加更详细的日志
2. 添加 SIGUSR1 信号处理——收到信号时立即执行一次 allocation cycle
3. 写 `tests/integration/test_kill_chain_flow.py` — 模拟完整流程

---

## 第四步：可演示版本

**目标：** 能跑一个完整的 kill chain 演示

**任务：**
1. 写 `run_demo.bat` — 启动 AFSIM + Python manager
2. 输出一个 `demo.log` 记录所有关键事件
3. 截图/输出展示：目标发现 → 分配 → 武器发射 → 命中

---

## 优先级

1. 第一步（修 bug）
2. 第二步（Shm 联调）
3. 第三步（DIS 联调）
4. 第四步（演示）

---

## 验收标准

- [ ] 104 tests pass（无失败）
- [ ] 能从 AFSIM 读取航迹到 Python
- [ ] 能从 Python 发送 weapon assign 到 AFSIM
- [ ] 有完整日志记录 OODA 循环
