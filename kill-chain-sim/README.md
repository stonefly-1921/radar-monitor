# Kill Chain Research & Simulation Validation Platform

基于 AFSIM 2.9.0 的 Kill Chain 研究与仿真验证平台。

## 项目结构

```
kill-chain-sim/
├── src/
│   ├── core/
│   │   └── dis/              # DIS 协议接口
│   │       ├── dis_protocol.py    # PDU 常量与结构体
│   │       ├── dis_socket.py     # UDP 多播封装
│   │       ├── dis_dispatcher.py # 消息路由
│   │       ├── dis_client.py     # 完整异步客户端
│   │       ├── entity_tracker.py # 航迹管理
│   │       ├── fire_control.py   # 武器发射控制
│   │       └── esm_client.py      # ESM 数据解析
│   ├── research/
│   │   ├── algorithms/       # 分配算法
│   │   │   └── milp_allocator.py  # MILP 优化
│   │   └── evaluation/       # 评估指标
│   │       └── metrics_evaluator.py
│   ├── sim/
│   │   ├── config/           # AFSIM 配置
│   │   └── scenarios/         # 仿真场景
│   └── main.py               # 主入口
├── tests/
│   ├── unit/                # 单元测试
│   └── integration/          # 集成测试
└── docs/
    └── plans/               # 设计文档
```

## 快速开始

### 1. 环境要求

- Python 3.10+
- AFSIM 2.9.0（可选，用于真实仿真）
- OR-Tools（用于 MILP 求解）

### 2. 安装依赖

```bash
pip install ortools
```

### 3. 运行测试

```bash
# 所有单元测试
python -m pytest tests/unit/ -v

# DIS 模块测试
python -m pytest tests/unit/test_dis*.py -v

# 集成测试
python -m pytest tests/integration/ -v
```

### 4. 启动 Kill Chain Manager

```bash
# 基本用法（监听 DIS 多播）
python -m src.main --multicast-addr 235.7.11.27 --port 3002

# 详细日志
python -m src.main -v

# 自定义 MILP 时间限制
python -m src.main --time-limit 60
```

### 5. AFSIM 配置

在 AFSIM 场景中添加：
```
include kill_chain_dis_interface.txt
```

## DIS 协议支持

| PDU 类型 | 方向 | 功能 |
|---------|------|------|
| Entity State (0x01) | AFSIM → Python | 航迹数据 |
| Fire (0x02) | 双向 | 武器发射 |
| Detonation (0x03) | AFSIM → Python | 交战结果 |
| Signal (0x04) | AFSIM → Python | ESM 数据 |

## 分配算法

1. **MILP（推荐）** — OR-Tools 求解联合传感器-武器-目标分配
2. **Greedy** — 动态分配，贪心选择
3. **Munkres** — 匈牙利算法，适合静态分配

## 评估指标

| 指标 | 说明 |
|------|------|
| Track Continuity | 航迹连续性 |
| Allocation Efficiency | 分配效率 |
| Engagement Effectiveness | 交战有效性 |
| OODA Loop Speed | 决策循环速度 |
| Coverage | 传感器覆盖率 |

## 测试结果

```
============================= 82 passed in 0.56s ==============================
```

## License

内部研究使用。