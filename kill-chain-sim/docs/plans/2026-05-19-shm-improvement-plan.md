# 共享内存路径改进计划

**日期：** 2026-05-19
**优先级：** SHM 双向通信验证 > DIS 优化

---

## 问题总结

AFSIM ←→ Python 共享内存双向通信未端到端验证。当前状态：

- SHM 文件存在（64MB）
- `TrackFileMonitor` 能把 AFSIM 日志写入 SHM（Python ← AFSIM 方向）
- `ShmClient` 有完整的读写 API
- 但 **Python → AFSIM 命令回写从未验证过**
- `shm_types.h` 中 sensor_count/weapon_count 在 Python 侧 Header 中缺失

---

## 改进任务

### T1：补充 Python ShmHeader（高优先级）

C Header 有 `sensor_count` 和 `weapon_count`，Python Header 没有。

修改 `ShmHeader` class，添加：
```python
("sensor_count", ctypes.c_uint16),
("weapon_count", ctypes.c_uint16),
```

并调整 `get_sensors()` 和 `get_weapons()` 使用这些字段而非常量。

验证：用 hexdump 检查 .dat 文件 header 区域字节。

---

### T2：添加 ShmClient 单元测试（验证 API 正确性）

已有的 `test_shm_client.py` 只验证基本读写。

新增测试：
- `test_shm_header_sensor_weapon_counts` — 验证 sensor_count/weapon_count 读写
- `test_get_tracks_with_header_count` — 验证 header.track_count 限制读取范围
- `test_weapon_assign_roundtrip` — 写 weapon assign → 读 cmd_ack

---

### T3：验证 Python → AFSIM 命令通路（关键验证）

用 mock AFSIM 方式：
1. 写一个模拟 AFSIM 的脚本，读取 SHM cmd 队列，打印命令并写入 ack
2. 运行 `python -c "from src.core.shared_mem import ShmClient; ..."` 发送命令
3. 验证命令被正确写入，ack 被正确读取

---

### T4：验证 DIS 完整闭环（非关键，可选）

DIS 方向的完整路径从未跑过：
```
Entity State → Allocation → Fire PDU → Detonation
```

检查 `main.py` 中的 `run_allocation_cycle()` 逻辑，添加详细日志。

---

## 依赖关系

```
T1 (Header 补充)
  ↓
T2 (单元测试覆盖)
  ↓
T3 (命令通路验证) ← 最重要
T4 (DIS 闭环验证) ← 可选
```

---

## 验收标准

- [ ] Python ShmHeader 包含 sensor_count 和 weapon_count
- [ ] `get_sensors()` 使用 sensor_count 而非常量
- [ ] `get_weapons()` 使用 weapon_count 而非常量
- [ ] 命令发送-ACK 循环能正常工作
- [ ] 所有单元测试通过
