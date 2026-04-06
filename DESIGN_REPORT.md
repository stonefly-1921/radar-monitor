# 雷达PPI显示器 - 设计报告（完整版）

**项目**: radarmonitornew
**路径**: `/root/.openclaw/agents/radarmonitornew/`
**最后更新**: 2026-04-05 23:12
**状态**: 识别功能已重新实现，TAS/仿真重置等需重建

---

## 一、整体架构

- **后端**: Python + uvicorn + FastAPI (`backend/`)
- **前端**: 纯HTML/JS (`frontend/index.html`)
- **内网穿透**: natapp (primary), serveo.net (备用)
- **访问URL**: http://kfc72c9d.natappfree.cc/static/index.html
- **后端端口**: 5000 (uvicorn)

---

## 二、API 接口清单

| 接口 | 方法 | 参数 | 状态 | 说明 |
|------|------|------|------|------|
| `/api/state` | GET | — | ✅ | 全量雷达状态快照 |
| `/api/power` | POST | `{"state": "on"/"off"}` | ✅ | 开关机 |
| `/api/mode` | POST | `{"mode": "spin"/"stop"}` | ✅ | 转动/停转模式 |
| `/api/steer` | POST | `{"azimuth": float, "elevation": float}` | ✅ | 停转模式天线指向 |
| `/api/search_zone` | POST | `{"azimuth_lo", "azimuth_hi", "elevation_lo", "elevation_hi", "range_min", "range_max"}` | ✅ | 设置搜索区 |
| `/api/highlight` | POST | `{"target_ids": [int]}` | ✅ | 高亮目标(红圈+♥) |
| `/api/identify` | POST | `{"target_id": int, "model": str}` | ✅ 已重新实现 | 点识别 |
| `/api/target_count` | POST | `{"count": int}` | ✅ | 目标数量(1-20) |
| `/api/tasEngage` | POST | `{"target_id": int, "data_rate": int}` | ❌ 缺失 | TAS跟踪 |
| `/api/tasDisengage` | POST | `{"target_id": int}` | ❌ 缺失 | 取消TAS |
| `/api/simulation/reset` | POST | `{}` | ❌ 缺失 | 仿真重置 |

---

## 三、数据模型

### 3.1 RadarState 字段

| 字段 | 默认值 | 状态 | 说明 |
|------|--------|------|------|
| `power` | False | ✅ | |
| `mode` | "stop" | ✅ | spin/stop |
| `antenna_angle_deg` | 0.0 | ✅ | spin模式天线方位 |
| `spin_rate_rpm` | 6.0 | ✅ | |
| `steer_azimuth_deg` | 0.0 | ✅ | stop模式天线方位 |
| `steer_elevation_deg` | 0.0 | ✅ | |
| `search_azimuth_lo_offset` | 0.0 | ✅ | 方位偏移下限 |
| `search_azimuth_hi_offset` | 360.0 | ✅ | 方位偏移上限 |
| `search_elevation_lo` | -5.0 | ✅ | |
| `search_elevation_hi` | 70.0 | ✅ | |
| `search_range_min_m` | 5000.0 | ✅ | 最小探测距离 |
| `search_range_max_m` | 450000.0 | ✅ | 最大探测距离 |
| `highlighted_ids` | [] | ✅ | 高亮目标列表 |
| `tas_tracking` | — | ❌ 不在RadarState | 内部用 `_tas_tracking` |
| `beamwidth_az_deg` | — | ❌ 缺失 | TAS波束宽度 |
| `beamwidth_el_deg` | — | ❌ 缺失 | TAS波束宽度 |

### 3.2 Target 字段

| 字段 | 类型 | 状态 | 说明 |
|------|------|------|------|
| `id` | int | ✅ | 批号 |
| `model` | str | ✅ | 仿真型号 |
| `identified_model` | str\|null | ✅ | 已确认识别 |
| `pending_identification` | str\|null | ✅ | 待生效识别 |
| `tracked` | bool | ✅ | 是否建立跟踪 |
| `detected` | bool | ✅ | 当前帧检测到 |
| `highlighted` | bool | ✅ | 是否高亮 |
| `distance_m` | float | ✅ | |
| `azimuth_deg` | float | ✅ | |
| `elevation_deg` | float | ✅ | |
| `height_m` | float | ✅ | |
| `speed_mps` | float | ✅ | |
| `heading_deg` | float | ✅ | |
| `detection_window` | List[bool] | ✅ | 5周期滑窗 |
| `last_detection_distance_m` | float | ✅ | |
| `last_detection_azimuth_deg` | float | ✅ | |
| `last_detection_time` | float | ✅ | |
| `_detection_points` | List[dict] | ✅ | 历史检测点 |
| `_first_detect_time` | float | ✅ | |
| `_detect_count` | int | ✅ | |
| `_detect_periods` | int | ✅ | |
| `_in_beam_last` | bool | ✅ | |
| `ident_antenna_angle` | — | ❌ 已移除 | |

---

## 四、已实现功能 ✅

### 4.1 识别功能 ✅

**流程**: 点击识别 → 显示"识别中…" → 等下一次检测到目标 → 显示型号+"✓已识别"

**后端** (`/api/identify`): 设 `pending_identification`
**后端检测循环**: `detected=True` 时，`pending → identified`，清除 `pending`
**前端** `identifyTarget()`: 调用 API，后端返回后 `fetchState()` 刷新
**PPI标牌**: 仅 `tracked=True` 显示，`#N 识别中…` 或 `#N 型号`
**列表**: "识别中…"(灰) / "型号 ✓已识别"(蓝) / "未知"(灰)

### 4.2 高亮功能 ✅

- `/api/highlight {target_ids}`: 目标高亮(红圈+♥符号)
- 列表项显示 ♥
- PPI上目标红圈高亮

### 4.3 搜索区 ✅

- 方位: ANGLE_OFFSET=-90 (法线朝上为0°)
- 扇形填充显示: `rgba(0,255,136,0.08)`
- stop模式: 方位相对法线(stearAz+offset)
- spin模式: 绝对方位
- 内外弧: ccw方向相反

### 4.4 检测点显示 ✅（有Bug）

- 绿色点: 未跟踪目标，`last_detection_*` 渲染，10秒超时
- 黄色点+连线: 已跟踪目标，`_detection_points` 渲染，60秒超时
- **⚠️ Bug**: 后端写 `p.azimuth`，前端读 `p.azimuth_deg` → NaN坐标

### 4.5 控制面板 ✅（95%）

开机/关机 | 转动模式/停转模式 | 天线指向设置 | 搜索区设置 | 目标列表

---

## 五、丢失需重建的功能 ❌

### 5.1 TAS 跟踪模式 ❌

**后端**:
```python
# 需新增 RadarState 字段
beamwidth_az_deg: float = 2.0
beamwidth_el_deg: float = 2.0

# TAS内部状态（simulator.py已有）
_tas_tracking: dict = {}  # {target_id: data_rate}
_tas_last_updates: dict = {}  # {target_id: last_update_time}

# API接口
POST /api/tasEngage {"target_id": int, "data_rate": int}  # data_rate: 1/5/10
POST /api/tasDisengage {"target_id": int}  # 可选

# TAS检测逻辑（stop模式）
for target_id, data_rate in list(s.tas_tracking.items()):
    interval = 1.0 / data_rate
    if sim_time - self._tas_last_updates.get(target_id, -999) < interval:
        continue
    s.steer_azimuth_deg = tas_target.azimuth_deg
    s.steer_elevation_deg = tas_target.elevation_deg
    az_diff = abs(normalize_angle(tas_target.azimuth_deg - s.steer_azimuth_deg))
    el_diff = abs(tas_target.elevation_deg - s.steer_elevation_deg)
    in_beam = az_diff <= s.beamwidth_az_deg / 2 and el_diff <= s.beamwidth_el_deg / 2
```

**前端**:
```javascript
// TAS按钮
const isTas = t.tracked && (radarState.tas_tracking || {})[t.id] !== undefined;
const tasBtn = isTas
  ? `<button class="btn btn-xs btn-tas-cancel" onclick="window.disengageTAS(${t.id})">取消TAS</button>`
  : `<button class="btn btn-xs btn-tas" onclick="window.showTASRate(${t.id})">TAS跟踪</button>`;

// TAS徽章
const tasRate = isTas ? radarState.tas_tracking[t.id] : null;
if (isTas) badge = `<span style="color:#ff9900">[TAS ${tasRate}Hz]</span>`;

window.showTASRate = (targetId) => {
  const rate = prompt('选择数据率(Hz): 1, 5, 10', '1');
  if (!['1','5','10'].includes(rate)) return;
  apiPost('/api/tasEngage', {target_id: targetId, data_rate: parseInt(rate)});
};

window.disengageTAS = (targetId) => {
  apiPost('/api/tasDisengage', {target_id: targetId});
};
```

### 5.2 仿真重置 ❌

**后端**:
```python
POST /api/simulation/reset
# 重置所有目标状态:
#   tracked=False, detected=False
#   identified_model=None, pending_identification=None
#   清空 detection_window, _detection_points
#   last_detection_* = 0
# 保留: power, mode, spin_rate_rpm, search_zone, tas_tracking
```

**前端**:
```html
<div class="control-group">
  <label>目标数量</label>
  <input id="sim-targets" type="number" value="5" min="1" max="20">
  <button id="btn-sim-reset">重置仿真</button>
</div>
```
```javascript
document.getElementById('btn-sim-reset').onclick = () => {
  const count = parseInt(document.getElementById('sim-targets').value);
  apiPost('/api/target_count', {count}).then(() => apiPost('/api/simulation/reset', {}));
};
```

### 5.3 目标数量调节 ❌

- 当前API `/api/target_count` 存在
- 但前端**无独立入口**，需通过仿真重置间接使用

---

## 六、Bug 清单

| # | 严重度 | 问题 | 根因 | 状态 |
|---|--------|------|------|------|
| 1 | 🔴严重 | 检测点坐标全错 | 后端写`p.azimuth`，前端读`p.azimuth_deg` → NaN | ❌ 未修 |
| 2 | 🟡中等 | TAS检测点不增加 | `beamwidth_az/el_deg` 缺失 | ❌ 缺失字段 |
| 3 | 🟡中等 | 绿色点闪烁 | `detected=True`只持续一帧 | ✅ 已修(用last_detection_*) |
| 4 | 🟡中等 | 识别后列表不更新 | `apiPost`成功不触发`updateTrackList` | ✅ 已修(加强制刷新) |
| 5 | 🟡中等 | `pending_identification`重置不清 | 仿真重置不清pending | ⚠️ 可能存在 |

---

## 七、控制面板布局

```
┌─────────────────────────────────────────────────────────┐
│ [开机] [关机]  │  [转动模式] [停转模式]                │
│ 天线方位: [  0]°  天线俯仰: [  0]°  [设置指向]         │
├─────────────────────────────────────────────────────────┤
│ 搜索区设置                                                  │
│ 方位: [-60° ~ +60°]  俯仰: [-5° ~ 70°]                 │
│ 距离: [5km ~ 450km]                                      │
│                              [设置搜索区]                  │
├─────────────────────────────────────────────────────────┤
│ 目标数量: [5]  [重置仿真]  ← 缺失前端按钮                │
├─────────────────────────────────────────────────────────┤
│ ▶ 目标列表                                               │
│ #1 F35     [识别] [TAS跟踪]              87km 45° 7600m│
│ #2 J20 ♥   [✓已识别] [取消TAS]           120km -30° 9000m│
│ ...                                                        │
└─────────────────────────────────────────────────────────┘
```

---

## 八、PPI 显示布局

```
           N
           ↑
    ←W     ↑     E→
           ↓
           S

PPI元素:
- 外圈: 绿色实线 3px
- 距离环: 100/200/300/400km (rgba绿色)
- 距离标签: 100/200/300/400 (左下象限)
- 搜索区扇形: 浅绿填充+边框
- 天线方向线: 黄色实线(转动)/虚线(停转)
- 绿色点: 未跟踪目标(last_detection_*), 10秒
- 黄色点+连线: 已跟踪目标(_detection_points), 60秒
- 红色高亮圈: highlighted目标
- 标牌: #N [识别中…/型号] (仅tracked目标)
```

---

## 九、当前代码状态

| 功能 | 后端 | 前端 | 状态 |
|------|------|------|------|
| 识别功能 | ✅ | ✅ | ✅ 工作 |
| 高亮 | ✅ | ✅ | ✅ 工作 |
| 搜索区 | ✅ | ✅ | ✅ 工作 |
| 检测点显示 | ✅ | ✅ | ❌ Bug(字段名错) |
| TAS跟踪 | ❌ | ❌ | ❌ 缺失 |
| 仿真重置 | ❌ | ❌ | ❌ 缺失 |
| 目标数量调节 | ✅ | ❌ | ⚠️ 无前端入口 |
| 控制面板 | ✅ | ✅ | ✅ 95% |
| PPI标牌 | ✅ | ✅ | ✅ 工作 |
| 目标列表 | ✅ | ✅ | ✅ 工作 |

---

## 十、重建优先级建议

1. **立即修**: 检测点字段名Bug (影响所有目标显示)
2. **立即修**: TAS后端 (beamwidth字段 + tasEngage/Disengage接口)
3. **高优先**: 仿真重置按钮
4. **高优先**: TAS前端 (TAS跟踪按钮 + showTASRate)
5. **中优先**: 目标数量调节前端入口
