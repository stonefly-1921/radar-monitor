# 雷达监控系统 - 设计说明

> 项目路径: `/root/.openclaw/agents/radarmonitornew/`
> 状态: 已完成，包含 TAS 跟踪功能
> 最后更新: 2026-04-06

---

## 1. 系统架构

### 1.1 整体架构

```
┌──────────────────────────────────────────────────────┐
│                     前端 (PPI显示器)                    │
│           纯 HTML/JS 单文件: frontend/index.html       │
│                      │                                │
│              HTTP API 轮询 (1s间隔)                    │
│                      ↓                                │
│              后端: FastAPI + uvicorn                   │
│           backend/api.py  (端口 8000)                  │
│                      │                                │
│         ┌─────────────┴──────────────┐              │
│         ↓          ↓          ↓       ↓              │
│   backend/     backend/     backend/   [仿真引擎]   │
│   api.py     simulator.py   models.py               │
└──────────────────────────────────────────────────────┘
                         ↑
              内网穿透: natapp (authtoken)
                         ↓
              外部访问: http://<natapp分配的域名>/
```

### 1.2 前后端分离

- **后端**: Python 3 + FastAPI + uvicorn，运行于 `0.0.0.0:8000`
- **前端**: 纯 HTML/JS 单文件，通过 FastAPI 静态文件服务 (`/static/`) 托管
- **通信**: 前端每 1 秒轮询一次 `GET /api/state` 获取全量状态快照
- **无 WebSocket**: 轮询模式，简单可靠，适合内网低延迟环境

### 1.3 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| 后端框架 | FastAPI 0.115 | 异步 API 框架 |
| 后端服务器 | uvicorn (standard) | ASGI 服务器 |
| 数据验证 | Pydantic 2.9 | 请求/响应模型校验 |
| 前端 | 原生 HTML5 + Canvas 2D | 无框架依赖 |
| 仿真 | Python 线程 (daemon) | 50ms 固定步长 |

---

## 2. 雷达探测原理

### 2.1 两种雷达模式

雷达有两种工作模式，由 `RadarState.mode` 控制：

| 模式 | 值 | 天线行为 | 检测方式 |
|------|-----|---------|---------|
| 转动模式 (TWS) | `"spin"` | 连续转动，默认 6 RPM（1 转 = 10 秒） | 天线扫过目标时检测 |
| 停转模式 (TAS) | `"stop"` | 天线固定指向法线方向 | 搜索区扫描 或 TAS 跟踪 |

#### 2.1.1 转动模式 (TWS 搜索)

- 天线以固定转速连续旋转：`deg_per_sec = 360 / (60 / spin_rate_rpm)`
- 默认 6 RPM → 1 转 = 10 秒 → 36°/秒
- **检测逻辑**: 天线方位与目标方位差值 < 3° 即为"在波束内"，触发一次检测
- **防重复计数**: 用 `_in_beam_last` 标记"上一帧是否已在波束内"，仅在"从不在→在"的跳变时计一次检测
- **搜索区**: 转动模式下不限制搜索区方位，天线扫描 360° 均可检测；俯仰和距离限制仍生效

#### 2.1.2 停转模式 (搜索 / TAS 跟踪)

- 天线固定指向 `steer_azimuth_deg` / `steer_elevation_deg`（法线方向）
- **常规检测**: 搜索区以法线为中心，天线在搜索区内扫描（10 秒一个完整扫描周期）
- **TAS 跟踪**: 雷达锁定特定目标，以高数据率持续跟踪（详见第 6 节）

### 2.2 探测物理参数

| 参数 | 值 |
|------|-----|
| 方位探测范围 | ±60°（相对法线） |
| 俯仰探测范围 | -5° ~ 70° |
| 距离探测范围 | 5 km ~ 450 km |
| TAS 波束宽度（方位） | ±3°（实际判定 ±1.5°，代码中 `< 3`） |
| TAS 波束宽度（俯仰） | ±3°（实际判定 `< 3`） |

---

## 3. 目标运动模型

系统支持两种目标运动模型，通过 `Target.maneuver_type` 区分：

### 3.1 跑道来回模型（主要模式，`maneuver_type = "runway"`）

目标在一条"跑道"上来回巡逻，无 180° 航向跳变，运动连续。

#### 3.1.1 模型参数

```
runway_center_azimuth_deg : 跑道中心线的方位角（°，相对雷达）
runway_center_distance_m  : 跑道中心点到雷达的距离（m）
runway_length_m           : 跑道长度（m），往返全程 = 2 × length
runway_width_m            : 跑道宽度（m），决定 segment A/B 的横向偏移
runway_progress           : 当前位置，沿跑道的进度 [0, 1]，0=起点，1=终点
_runway_direction          : 运动方向，+1=正向（起点→终点），-1=反向
```

#### 3.1.2 位置计算数学公式

```
# 沿跑道位置：progress 0→1 映射到 -length/2 → +length/2（连续，无跳变）
along_track = (runway_progress × 2 - 1) × (runway_length_m / 2)

# 跑道中心点的 XY 坐标（以雷达为原点）
cx = runway_center_distance_m × sin(runway_center_azimuth)
cy = runway_center_distance_m × cos(runway_center_azimuth)

# 目标 XY 坐标
dx = along_track × cos(runway_center_azimuth)
dy = along_track × sin(runway_center_azimuth)
x = cx + dx
y = cy + dy

# 雷达测量值
distance_m      = sqrt(x² + y² + height²)
azimuth_deg     = atan2(y, x)              （以雷达为原点，方位角）
elevation_deg   = atan2(height, sqrt(x²+y²))

# 航向（连续，无 180° 跳变）
heading_deg = (runway_center_azimuth_deg + (1 - direction) × 180) mod 360
# direction=+1 → heading = runway_center_azimuth_deg（正向）
# direction=-1 → heading = runway_center_azimuth_deg + 180°（反向）
```

#### 3.1.3 运动更新逻辑

每帧（dt 秒）更新：

```
delta_progress = (speed_mps / (runway_length_m × 2)) × dt
runway_progress += delta_progress × direction

# 碰端点反向（无跳变）
if runway_progress >= 1.0:
    runway_progress = 1.0
    direction = -1
elif runway_progress <= 0.0:
    runway_progress = 0.0
    direction = +1
```

### 3.2 圆弧巡逻模型（遗留模式）

```
# 角速度
omega = speed_mps / orbit_radius_m   (弧度/秒)

# 航向更新
heading_deg += degrees(omega × dt)

# 位置（圆心 + 半径 × 航向）
dx = center_x + orbit_radius × cos(heading)
dy = center_y + orbit_radius × sin(heading)
```

---

## 4. 航迹管理（起批状态机）

### 4.1 起批常量

| 常量 | 值 | 说明 |
|------|-----|------|
| `_TRACK_PERIOD` | 10.0 秒 | 一个检测周期（与天线转速匹配） |
| `_TRACK_PERIODS` | 5 | 起批所需的最大周期窗口 |
| `_TRACK_ESTABLISH` | 3 | 窗口内至少检测到的次数 → 建立跟踪 |
| `_TRACK_TIMEOUT` | 30.0 秒 | 已跟踪目标超时无检测 → 消批 |

### 4.2 状态机流程

```
未跟踪 ──检测到──→ [5周期滑窗中，检测计数+1]
                          │
                    达到3次检测？ ──是──→ 已跟踪
                          │否
                    超过5周期？ ──是──→ 重置（回到未跟踪）
                          │否
                          └── 继续累积检测次数
```

### 4.3 详细逻辑（`_update_target_tracking`）

**未跟踪目标**：
- 每次检测到：`detect_periods = 1`，`detect_count++`，记录检测点
- 每次未检测到但有首检时间：`detect_periods = int((sim_time - first_detect_time) / 10) + 1`
- `detect_count >= 3` → 立即建立跟踪（不等 5 周期用完）
- `detect_periods > 5` 但 `detect_count < 3` → 重置

**已跟踪目标**：
- 检测到 → 更新 `last_detection_time`，追加检测点
- 超过 30 秒无检测 → 消批（`tracked = False`，清空所有检测点）

### 4.4 检测点保留策略

| 目标状态 | 检测点来源 | 保留时间 |
|---------|-----------|---------|
| 未跟踪 | `last_detection_*`（单一最新点） | 10 秒（覆盖最长起批时间） |
| 已跟踪 | `_detection_points`（完整历史） | 保留至消批（消批时统一清空） |

---

## 5. TAS 跟踪

### 5.1 概念

TAS（Target Acquisition System，目标捕获系统）是在**停转模式**下，对已起批目标进行高数据率锁定跟踪的机制。

### 5.2 TAS 约束条件

启动 TAS 跟踪前必须满足：

1. **必须在停转模式**（`mode == "stop"`）
2. **目标必须已起批**（`tracked == True`）
3. **目标必须在探测范围内**：
   - 方位差 ≤ 60°（相对法线）
   - 俯仰 -5° ~ 70°
   - 距离 5 km ~ 450 km
4. **TAS 总数限制**：最多 10 个 TAS 目标同时跟踪
5. **10Hz 限制**：最多 10 个目标可设 10Hz 数据率

### 5.3 数据率

| data_rate | 检测间隔 | 说明 |
|-----------|---------|------|
| 1 | 1.0 秒 | 低数据率，节能 |
| 5 | 0.2 秒 | 中等数据率 |
| 10 | 0.1 秒 | 高数据率，高精度跟踪 |

### 5.4 TAS 检测逻辑

```
for target_id, data_rate in tas_tracking:
    interval = 1.0 / data_rate
    if (sim_time - tas_last_updates[target_id]) >= interval:
        # 检查目标是否在探测范围内
        az_diff = abs(normalize_angle(target.azimuth - steer_azimuth))
        in_range = (az_diff <= 60
                    and 5e3 <= target.distance_m <= 450e3
                    and -5 <= target.elevation_deg <= 70)
        if in_range:
            detected = True
            更新检测点和跟踪状态
```

---

## 6. 识别流程

### 6.1 识别状态机

```
未识别
  │ 调用 /api/identify
  ↓
pending_identification = "型号名"
  │ 下次检测到该目标（detected=True）
  ↓
identified_model = "型号名"    ← 确认
pending_identification = None
```

### 6.2 识别特点

- **非实时**：识别请求后需等待下一次检测到目标才生效
- **跨模式保留**：关机（`power=off`）时 `identified_model` 保留，`pending_identification` 不保留
- **开机重置**：开机时清空所有识别状态

---

## 7. 检测点渲染（PPI 显示）

### 7.1 渲染逻辑

前端 Canvas 每秒从 `GET /api/state` 获取数据，根据目标状态渲染检测点：

#### 未跟踪目标（绿色点）
- **来源**: `last_detection_distance_m` + `last_detection_azimuth_deg`（单一最新点）
- **颜色**: 绿色 `#00ff88`
- **保留时间**: 10 秒（前端自行控制）
- **样式**: 单独绿色点，无连线

#### 已跟踪目标（黄色点 + 连线）
- **来源**: `_detection_points` 数组（完整历史点）
- **颜色**: 黄色 `#ffcc00`
- **保留时间**: 保留至消批（消批时统一清空）
- **样式**: 点 + 从旧到新的连线

### 7.2 高亮点

- **来源**: `highlighted_ids`（RadarState）或 `Target.highlighted`
- **颜色**: 红色 `#ff4444` 圈
- **附带**: ♥ 符号标注

### 7.3 PPI 渲染元素一览

```
┌─────────────────────────────────┐
│  外圈 (3px 绿色实线)              │
│  距离环 (100/200/300/400km)      │
│  距离标签 (左下象限)               │
│  坐标轴 (淡绿虚线)                 │
│  搜索区扇形 (浅绿填充)             │
│  天线方向线 (黄实线/虚线)          │
│  绿色点 (未跟踪，10s)             │
│  黄色点+连线 (已跟踪)             │
│  红色高亮圈 (highlighted)         │
│  航迹标牌 (#N [型号/识别中])       │
└─────────────────────────────────┘
```

---

## 8. 数据模型

### 8.1 RadarState

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `power` | bool | `False` | 开关机 |
| `mode` | str | `"stop"` | `spin` / `stop` |
| `antenna_angle_deg` | float | `0.0` | 转动模式天线方位 |
| `spin_rate_rpm` | float | `6.0` | 转动速度（转/分） |
| `steer_azimuth_deg` | float | `0.0` | 停转模式法线方位 |
| `steer_elevation_deg` | float | `0.0` | 停转模式法线俯仰 |
| `search_azimuth_lo_offset` | float | `-60.0` | 搜索区方位下限（相对法线） |
| `search_azimuth_hi_offset` | float | `60.0` | 搜索区方位上限 |
| `search_elevation_lo` | float | `-5.0` | 搜索区俯仰下限 |
| `search_elevation_hi` | float | `70.0` | 搜索区俯仰上限 |
| `search_range_min_m` | float | `5000.0` | 搜索区最近距离 |
| `search_range_max_m` | float | `450000.0` | 搜索区最远距离 |
| `search_zone_set` | bool | `False` | 是否已设置搜索区 |
| `highlighted_ids` | List[int] | `[]` | 高亮目标 ID 列表 |

### 8.2 Target

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | int | 目标批号 |
| `model` | str | 仿真型号（随机分配） |
| `distance_m` | float | 当前距离（m） |
| `azimuth_deg` | float | 当前方位角（°） |
| `elevation_deg` | float | 当前俯仰角（°） |
| `height_m` | float | 高度（m） |
| `speed_mps` | float | 速度（m/s） |
| `heading_deg` | float | 航向角（°） |
| `detected` | bool | 本帧是否检测到 |
| `tracked` | bool | 是否已建立跟踪 |
| `highlighted` | bool | 是否高亮 |
| `identified_model` | str\|None | 已确认的识别型号 |
| `pending_identification` | str\|None | 待生效的识别型号 |
| `last_detection_distance_m` | float | 最后检测距离 |
| `last_detection_azimuth_deg` | float | 最后检测方位 |
| `_detection_points` | List[dict] | 检测点历史 |
| `_tas_tracking` | dict | **内部**：TAS 跟踪表 `{target_id: data_rate}` |

---

## 9. 仿真引擎

### 9.1 架构

- **单例模式**: `get_simulator()` 返回全局 `RadarSimulator` 实例
- **线程**: `daemon=True` 的后台线程运行仿真循环
- **步长**: 固定 50ms（`time.sleep(0.05)`）
- **锁**: `threading.Lock` 保护共享状态

### 9.2 仿真循环

```
_simulation_loop():
    while _running:
        dt = now - last_update
        with _lock:
            frame_count++
            sim_time += dt
            _update_state(dt)    # 更新天线 + 目标位置 + 检测判断
        sleep(50ms)
```

---

## 10. 端口说明

- **代码默认**: `uvicorn.run(app, host="0.0.0.0", port=8000)`
- **任务说明**: 任务文档提到 port 5000，实际代码使用 8000
- **前端访问**: `http://<host>:8000/` 或 `http://<host>:8000/static/index.html`

---

## 11. 已知限制

1. **检测点字段名**: 后端写入 `azimuth_deg`，前端读取逻辑需确认一致性
2. **转动模式搜索区**: 方位限制不生效（天线扫描 360°）
3. **TAS 目标超出范围**: TAS 跟踪中若目标移出 ±60° 方位范围，检测暂停但不自动 Disengage
