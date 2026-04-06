# 雷达监控系统 - 对外接口说明

> 项目路径: `/root/.openclaw/agents/radarmonitornew/`
> 后端: FastAPI + uvicorn
> 基础 URL: `http://<host>:8000`
> 前端轮询: 每 1 秒一次 `GET /api/state`

---

## 接口概览

| 接口 | 方法 | 说明 |
|------|------|------|
| `GET /api/state` | GET | 全量状态快照 |
| `POST /api/power` | POST | 开关机 |
| `POST /api/mode` | POST | 雷达模式（转动/停转） |
| `POST /api/steer` | POST | 法线指向设置 |
| `POST /api/search_zone` | POST | 搜索区参数设置 |
| `POST /api/highlight` | POST | 高亮目标 |
| `POST /api/identify` | POST | 目标识别 |
| `POST /api/target_count` | POST | 目标数量 |
| `POST /api/tasEngage` | POST | TAS 跟踪 |
| `POST /api/tasDisengage` | POST | 取消 TAS 跟踪 |
| `POST /api/simulation/reset` | POST | 重置仿真 |

---

## GET /api/state

**说明**: 返回仿真器完整状态快照，是前端轮询获取数据的主要接口。

**请求**: 无需参数

**响应**: `200 OK`

```json
{
  "sim_time": 123.456,
  "power": true,
  "mode": "spin",
  "antenna_angle_deg": 45.0,
  "spin_rate_rpm": 6.0,
  "steer_azimuth_deg": 0.0,
  "steer_elevation_deg": 0.0,
  "search_zone": {
    "azimuth": [-60.0, 60.0],
    "elevation": [-5.0, 70.0],
    "range_m": [5000.0, 450000.0]
  },
  "search_zone_set": true,
  "targets": [
    {
      "id": 1,
      "model": "F35",
      "distance_m": 87500.0,
      "azimuth_deg": 45.2,
      "elevation_deg": 8.5,
      "height_m": 7600.0,
      "speed_mps": 320.0,
      "heading_deg": 45.0,
      "detected": true,
      "tracked": true,
      "highlighted": false,
      "identified_model": "F35",
      "pending_identification": null,
      "detection_window": [true, false, true, false, true],
      "last_detection_distance_m": 87500.0,
      "last_detection_azimuth_deg": 45.2,
      "detection_points": [
        {
          "time": 120.0,
          "r": 89000.0,
          "azimuth_deg": 44.8,
          "elevation_deg": 8.3,
          "height_m": 7600.0,
          "speed_mps": 320.0,
          "heading_deg": 45.0,
          "model": "F35",
          "is_tas": false,
          "data_rate": null
        }
      ]
    }
  ],
  "highlighted_ids": [],
  "tas_tracking": {
    "1": 5,
    "3": 10
  }
}
```

**错误响应**: 无特定错误，正常情况必返回 200。

---

## POST /api/power

**说明**: 控制雷达开关机。开机时清空所有检测点和跟踪状态（保留识别型号）。

**请求**:

```json
Content-Type: application/json
{
  "state": "on"    // "on" | "off"
}
```

**响应**: `200 OK`

```json
{
  "ok": true,
  "power": true
}
```

**错误处理**:
- `state` 不为 `"on"` 或 `"off"`：后端将其转为布尔值，超出预期值无明确错误返回
- 网络错误：HTTP 500，由 FastAPI 框架处理

---

## POST /api/mode

**说明**: 设置雷达工作模式。

**请求**:

```json
Content-Type: application/json
{
  "mode": "spin"   // "spin" | "stop"
}
```

| mode | 含义 | 天线行为 |
|------|------|---------|
| `"spin"` | 转动模式（TWS 搜索） | 天线连续旋转（默认 6 RPM） |
| `"stop"` | 停转模式 | 天线固定指向法线 |

**响应**: `200 OK`

```json
{
  "ok": true,
  "mode": "spin"
}
```

**错误处理**:
- `mode` 不为 `"spin"` 或 `"stop"`：静默忽略，不更新模式

---

## POST /api/steer

**说明**: 设置停转模式的法线指向（方位和俯仰）。

**请求**:

```json
Content-Type: application/json
{
  "azimuth": 45.0,    // float, 方位角（°），以雷达为原点，0°=北，顺时针
  "elevation": 0.0    // float, 俯仰角（°），0°=水平面，正=上
}
```

**响应**: `200 OK`

```json
{
  "ok": true,
  "steer_azimuth_deg": 45.0,
  "steer_elevation_deg": 0.0
}
```

**说明**: 方位角以雷达为原点，0° 为正北，顺时针增加。俯仰角 0° 为水平，正值朝上。

---

## POST /api/search_zone

**说明**: 设置停转模式下的搜索区参数（方位偏移、俯仰范围、距离范围）。

**请求**:

```json
Content-Type: application/json
{
  "azimuth_lo": -60.0,    // float, 方位下限偏移（°，相对法线）
  "azimuth_hi": 60.0,     // float, 方位上限偏移（°，相对法线）
  "elevation_lo": -5.0,   // float, 俯仰下限（°）
  "elevation_hi": 70.0,    // float, 俯仰上限（°）
  "range_min": 5000.0,     // float, 最近距离（m）
  "range_max": 450000.0    // float, 最远距离（m）
}
```

**响应**: `200 OK`

```json
{
  "ok": true
}
```

**说明**:
- 方位偏移是**相对法线**的差值，如 `azimuth_lo=-60, azimuth_hi=60` 表示以法线为中心 ±60° 的扇形
- `range_min` 和 `range_max` 单位为米
- 设置搜索区后 `search_zone_set` 标记为 `true`，停转模式才会检测非 TAS 目标

---

## POST /api/highlight

**说明**: 设置高亮目标，目标在 PPI 上显示红色高亮圈和 ♥ 符号。

**请求**:

```json
Content-Type: application/json
{
  "target_ids": [1, 3]   // List[int], 目标 ID 列表
}
```

**响应**: `200 OK`

```json
{
  "ok": true,
  "highlighted_ids": [1, 3]
}
```

**说明**: 传入空数组 `[]` 可取消所有高亮。

---

## POST /api/identify

**说明**: 对指定目标发起识别请求。识别为**异步生效**：请求后需等下一次检测到该目标，型号才会从 `pending` 变为 `confirmed`。

**请求**:

```json
Content-Type: application/json
{
  "target_id": 1,         // int, 目标 ID
  "model": "F35"         // str, 要识别的型号名称
}
```

**响应**: `200 OK`（目标存在）

```json
{
  "ok": true,
  "target_id": 1,
  "pending_identification": "F35"
}
```

**错误响应**: `200 OK`（目标不存在，返回错误）

```json
{
  "ok": false,
  "error": "目标不存在"
}
```

**识别流程**:
1. 调用 `/api/identify` → `pending_identification` 被设置
2. 雷达检测到该目标（`detected=True`）→ `identified_model` 被赋值，`pending_identification` 清空
3. 前端通过轮询 `GET /api/state` 发现变化，更新显示

---

## POST /api/target_count

**说明**: 重新生成指定数量的目标，并清空所有跟踪和检测状态。

**请求**:

```json
Content-Type: application/json
{
  "count": 5              // int, 目标数量，范围 1-20
}
```

**响应**: `200 OK`

```json
{
  "ok": true,
  "count": 5
}
```

**说明**:
- 目标数量范围 1-20
- 调用此接口后，所有现有目标被替换为新生成的目标（保留高亮设置）
- 新目标均处于"未检测、未跟踪"状态，需要重新起批

---

## POST /api/tasEngage

**说明**: 对已起批目标启动 TAS 跟踪（TAS 只能在停转模式下使用）。

**请求**:

```json
Content-Type: application/json
{
  "target_id": 1,         // int, 目标 ID（目标必须已 tracked=True）
  "data_rate": 5          // int, 数据率：1 | 5 | 10 (Hz)
}
```

**响应**: `200 OK`

```json
{
  "ok": true,
  "target_id": 1,
  "data_rate": 5
}
```

**错误响应**: `200 OK`（有错误时也返回 200，但 `ok=false`）

```json
{
  "ok": false,
  "error": "TAS跟踪只能在停转模式下使用"
}
```

| 错误信息 | 含义 |
|---------|------|
| `"缺少target_id"` | 请求体未提供 `target_id` |
| `"data_rate必须是1/5/10"` | `data_rate` 值不合法 |
| `"目标 #N 不存在"` | 目标 ID 不存在 |
| `"目标 #N 尚未起批，无法进入TAS跟踪"` | 目标未建立跟踪 |
| `"目标 #N 不在方位探测范围（±60°）内"` | 目标超出 TAS 方位范围 |
| `"目标 #N 不在俯仰探测范围（-5°~70°）内"` | 目标超出俯仰范围 |
| `"目标 #N 不在距离探测范围（5~450km）内"` | 目标超出距离范围 |
| `"TAS跟踪目标已达上限（10个）"` | TAS 总数已达 10 个 |
| `"10Hz数据率目标已达上限（10个）"` | 10Hz 目标已达 10 个 |

**TAS 约束条件**:
1. 必须在停转模式（`mode="stop"`）
2. 目标必须已建立跟踪（`tracked=True`）
3. 目标必须在探测范围内（方位差 ≤ 60°、俯仰 -5°~70°、距离 5~450km）
4. TAS 总数 ≤ 10
5. 10Hz 目标数 ≤ 10

---

## POST /api/tasDisengage

**说明**: 取消指定目标的 TAS 跟踪，目标恢复为搜索区 TWS 常规检测。

**请求**:

```json
Content-Type: application/json
{
  "target_id": 1          // int, 目标 ID
}
```

**响应**: `200 OK`

```json
{
  "ok": true,
  "target_id": 1
}
```

**错误响应**: `200 OK`

```json
{
  "ok": false,
  "error": "目标 #1 不在TAS跟踪中"
}
```

---

## POST /api/simulation/reset

**说明**: 重置仿真状态，清除所有目标的跟踪和识别状态（保留目标数量和雷达参数）。

**请求**: 无需请求体（可为空 JSON `{}`）

**响应**: `200 OK`

```json
{
  "ok": true
}
```

**重置效果**:
| 字段 | 重置后 |
|------|--------|
| `tracked` | `false` |
| `detected` | `false` |
| `identified_model` | `null` |
| `pending_identification` | `null` |
| `highlighted` | `false` |
| `detection_window` | `[]` |
| `_detection_points` | `[]` |
| `last_detection_*` | `0.0` |

**保留内容**: `power`, `mode`, `spin_rate_rpm`, `search_zone`, `tas_tracking`, `highlighted_ids`

---

## 通用响应格式

### 成功

```json
{
  "ok": true,
  ...其他字段
}
```

### 失败

```json
{
  "ok": false,
  "error": "错误描述"
}
```

---

## 前端轮询逻辑参考

```javascript
async function fetchState() {
  try {
    const res = await fetch('/api/state');
    radarState = await res.json();
    updatePPI(radarState);
    updateHeader(radarState);
    updateTrackList(radarState);
  } catch (e) {
    console.error('获取状态失败:', e);
  }
}

// 每秒轮询
setInterval(fetchState, 1000);
fetchState(); // 立即执行一次
```

---

## 错误码

| HTTP 状态码 | 含义 |
|------------|------|
| 200 | 请求成功（业务错误通过 `ok: false` 返回） |
| 400 | 请求格式错误（Pydantic 校验失败） |
| 404 | 资源不存在（通常不会触发） |
| 422 | 请求体验证失败（参数类型错误） |
| 500 | 服务器内部错误 |

---

## 状态快照字段速查

| 字段 | 类型 | 说明 |
|------|------|------|
| `sim_time` | float | 仿真时间（秒） |
| `power` | bool | 雷达开关 |
| `mode` | string | `"spin"` 或 `"stop"` |
| `antenna_angle_deg` | float | 转动模式天线方位（°） |
| `steer_azimuth_deg` | float | 停转模式法线方位（°） |
| `steer_elevation_deg` | float | 停转模式法线俯仰（°） |
| `search_zone_set` | bool | 搜索区是否已配置 |
| `tas_tracking` | dict | TAS 跟踪 `{target_id: data_rate}` |
| `highlighted_ids` | list | 高亮目标 ID 列表 |
| `targets[].tracked` | bool | 是否已建立跟踪 |
| `targets[].detected` | bool | 本帧是否检测到 |
| `targets[].identified_model` | str\|null | 已确认的识别型号 |
| `targets[].pending_identification` | str\|null | 待生效的识别型号 |
| `targets[].detection_points` | list | 检测点历史（用于渲染黄色轨迹线） |
| `targets[].last_detection_distance_m` | float | 最新检测点的距离（用于渲染绿色点） |
