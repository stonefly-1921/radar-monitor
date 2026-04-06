"""
雷达仿真 - 仿真引擎
"""
import math
import threading
import time
from typing import List, Dict, Any, Optional

from models import Target, RadarState, create_targets


class RadarSimulator:
    """雷达仿真器"""

    # 起批状态机常量
    _TRACK_PERIOD = 10.0   # 检测周期（秒）
    _TRACK_PERIODS = 5     # 起批所需周期数
    _TRACK_ESTABLISH = 3   # 周期内至少检测到次数 → 建立跟踪
    _TRACK_TIMEOUT = 30.0 # 跟踪目标超过此时间无检测 → 消批

    def __init__(self, target_count: int = 5, seed: int = 42):
        self.state = RadarState()
        self.targets: List[Target] = create_targets(target_count, seed=seed)
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_update = time.time()
        self._frame_count = 0  # 仿真帧计数
        self._sim_time = 0.0   # 仿真时间（秒）

        self._tas_tracking: Dict[int, int] = {}  # {target_id: data_rate}
        self._tas_last_updates: Dict[int, float] = {}  # {target_id: last_update_time}

    def start(self):
        """启动仿真"""
        self._running = True
        self._thread = threading.Thread(target=self._simulation_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """停止仿真"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)

    def _simulation_loop(self):
        """仿真主循环，每50ms更新一次"""
        while self._running:
            now = time.time()
            dt = now - self._last_update
            self._last_update = now

            with self._lock:
                self._frame_count += 1
                self._sim_time += dt
                self._update_state(dt)

            time.sleep(0.05)

    def _update_state(self, dt: float):
        """更新仿真状态"""
        # Power off: clear all tracks and detections immediately
        if not self.state.power:
            for t in self.targets:
                t.detected = False
                t.tracked = False
                t._detection_points.clear()
                t.detection_window.clear()
                t.last_detection_distance_m = 0.0
                t.last_detection_azimuth_deg = 0.0
                t.last_detection_time = 0.0
                # Note: do NOT clear identified_model or pending_identification
            self._tas_tracking.clear()
            self._tas_last_updates.clear()
            self.state.search_zone_set = False
            self.state.steer_azimuth_deg = 0.0
            self.state.steer_elevation_deg = 0.0
            return
        # 更新天线角度（转动模式）
        if self.state.mode == "spin":
            # 6转/分 = 360°/10秒 = 36°/秒
            deg_per_sec = 360.0 / (60.0 / self.state.spin_rate_rpm)
            self.state.antenna_angle_deg = (self.state.antenna_angle_deg + deg_per_sec * dt) % 360

        # 更新目标位置
        for t in self.targets:
            t.update(dt)

        # 检测判断
        self._update_detections()

    def _update_detections(self):
        """更新目标检测状态 + 起批状态机"""
        if self.state.mode == "spin":
            # 转动模式：天线扫过目标方位时检测（±3°范围内），搜索区仅用于判断角度，不限制检测
            # 停转模式才需要 search_zone_set 检查
            ant_az = self.state.antenna_angle_deg
            for t in self.targets:
                diff = (t.azimuth_deg - ant_az + 180) % 360 - 180
                in_beam = abs(diff) < 3  # 只要在天线波束内就检测
                # 每帧检测，用 "之前不在波束内" 防止同一目标连续多帧重复计数
                # 天线每转一圈（约10秒）目标被检测约3帧，靠"3次/5周期"滑窗防止误批
                detected = in_beam and not getattr(t, '_in_beam_last', False)
                t._in_beam_last = in_beam
                t.detected = detected
                # 检测到目标时：如果有待识别任务且型号为未知，立即应用识别结果
                if detected and t.pending_identification and not t.identified_model:
                    t.identified_model = t.pending_identification
                    t.pending_identification = None
                self._update_target_tracking(t, detected)
        else:
            # 停转模式：搜索区以法线为中心，扫描完整个搜索区需10秒
            # 搜索区内目标：扫描线经过方位时检测一次（约1秒），之后保持6秒检测状态
            # 搜索区外目标：不检测，30秒超时消批
            now = time.time()
            scan_cycle = (now - (self.state.scan_start_time or now)) % 10.0

            for t in self.targets:
                # TAS目标：按data_rate间隔检测，只要在探测范围内就能检测到
                if t.id in self._tas_tracking:
                    data_rate = self._tas_tracking[t.id]
                    interval = 1.0 / data_rate
                    elapsed = self._sim_time - self._tas_last_updates.get(t.id, -999)
                    if elapsed >= interval:
                        # 达到检测间隔，检测目标是否在探测范围内
                        az_diff = abs(self._normalize_angle(t.azimuth_deg - self.state.steer_azimuth_deg))
                        in_range = (az_diff <= 60 and
                                    5e3 <= t.distance_m <= 450e3 and
                                    -5 <= t.elevation_deg <= 70)
                        t.detected = bool(in_range)
                        if t.detected:
                            self._tas_last_updates[t.id] = self._sim_time
                            if t.pending_identification and not t.identified_model:
                                t.identified_model = t.pending_identification
                                t.pending_identification = None
                            self._update_target_tracking(t, True)
                    # 间隔未到：不更新检测状态，保留已有检测点和状态（不调用_update_target_tracking）
                else:
                    # 非TAS目标：按搜索区常规检测
                    # 停转模式且未设置搜索区时，不检测任何目标
                    if not self.state.search_zone_set:
                        self._update_target_tracking(t, False)
                        continue
                    in_zone = self._is_in_search_zone(t)
                    detected = in_zone and (self._frame_count % 200 == 0)
                    t.detected = detected
                    if detected and t.pending_identification and not t.identified_model:
                        t.identified_model = t.pending_identification
                        t.pending_identification = None
                    self._update_target_tracking(t, detected)

    def _build_detection_point(self, t: Target, sim_time: float) -> Dict[str, Any]:
        """构建航迹档案记录，包含完整信息"""
        is_tas = t.id in self._tas_tracking
        return {
            'time': sim_time,
            'r': t.distance_m,
            'azimuth_deg': t.azimuth_deg,
            'elevation_deg': t.elevation_deg,
            'height_m': t.height_m,
            'speed_mps': t.speed_mps,
            'heading_deg': t.heading_deg,
            'model': t.identified_model,
            'is_tas': is_tas,
            'data_rate': self._tas_tracking.get(t.id) if is_tas else None,
        }

    def _update_target_tracking(self, t: Target, detected: bool, sim_time: float = None):
        """起批状态机：每次检测到目标时重启5周期窗口，5周期内3次检测起批；30秒超时消批"""
        if sim_time is None:
            sim_time = self._sim_time

        if not t.tracked:
            if detected:
                # 每次检测到：重启5周期窗口，计数+1，记录检测点
                t._first_detect_time = sim_time
                t._detect_periods = 1
                t._detect_count += 1
                t._detection_points.append(self._build_detection_point(t, sim_time))
                # 起批前检测点保留30秒（覆盖起批所需的最长时间）
                cutoff = sim_time - 30.0
                t._detection_points = [p for p in t._detection_points if p['time'] > cutoff]
            else:
                if t._first_detect_time > 0:
                    elapsed = sim_time - t._first_detect_time
                    t._detect_periods = int(elapsed / self._TRACK_PERIOD) + 1

            # 3次检测到立即起批（不等40秒走完）
            if t._detect_count >= self._TRACK_ESTABLISH:
                t.tracked = True
                t.last_detection_distance_m = t.distance_m
                t.last_detection_azimuth_deg = t.azimuth_deg
                t.last_detection_time = sim_time
                t.highlighted = t.id in self.state.highlighted_ids
                t._first_detect_time = -1.0
                t._detect_periods = 0
                t._detect_count = 0
            elif t._detect_periods > self._TRACK_PERIODS:
                # 5周期用完不够3次，重置
                t._first_detect_time = -1.0
                t._detect_periods = 0
                t._detect_count = 0
        else:
            # 已跟踪：检测到则更新最后检测时间和检测点，超时消批
            if detected:
                t.last_detection_distance_m = t.distance_m
                t.last_detection_azimuth_deg = t.azimuth_deg
                t.last_detection_time = sim_time
                t._detection_points.append(self._build_detection_point(t, sim_time))
                # 已跟踪检测点不设 cutoff，一直保留到消批（消批时统一清空）
            else:
                # 检测不到目标：不清空检测点（保留历史，让点一直显示到消批），只更新时间
                if sim_time - t.last_detection_time > self._TRACK_TIMEOUT:
                    t.tracked = False
                    t.last_detection_distance_m = 0.0
                    t.last_detection_azimuth_deg = 0.0
                    t.last_detection_time = 0.0


    @staticmethod
    def _normalize_angle(deg: float) -> float:
        """将角度标准化到[-180, 180]"""
        while deg > 180:
            deg -= 360
        while deg < -180:
            deg += 360
        return deg

    def _is_in_search_zone(self, t: Target) -> bool:
        """判断目标是否在搜索区/探测范围内"""
        s = self.state
        if s.mode == 'stop':
            # 停转模式：方位相对法线，有搜索区才检测
            az_lo = s.steer_azimuth_deg + s.search_azimuth_lo_offset
            az_hi = s.steer_azimuth_deg + s.search_azimuth_hi_offset
            az_ok = az_lo <= t.azimuth_deg <= az_hi
        else:
            # 转动模式：天线扫描360°，不限制方位
            az_ok = True
        return (
            az_ok and
            s.search_elevation_lo <= t.elevation_deg <= s.search_elevation_hi and
            s.search_range_min_m <= t.distance_m <= s.search_range_max_m
        )

    # ========== 控制接口 ==========

    def set_power(self, on: bool):
        """开机/关机"""
        with self._lock:
            self.state.power = on
            if not on:
                for t in self.targets:
                    t.detected = False
                    t.tracked = False
                    t._detection_points.clear()
                    t.detection_window.clear()
                    t.pending_identification = None
            else:
                # 开机时清空所有检测点，重新开始
                for t in self.targets:
                    t.detected = False
                    t.tracked = False
                    t._detection_points.clear()
                    t.detection_window.clear()
                    t.last_detection_distance_m = 0.0
                    t.last_detection_azimuth_deg = 0.0
                    t.last_detection_time = 0.0
                    t.pending_identification = None
                    t.identified_model = None

    def set_mode(self, mode: str):
        """设置雷达模式：spin / stop"""
        with self._lock:
            if mode in ("spin", "stop"):
                self.state.mode = mode

    def set_steer(self, azimuth: float, elevation: float):
        """设置法线指向（停转模式）"""
        with self._lock:
            self.state.steer_azimuth_deg = azimuth
            self.state.steer_elevation_deg = elevation

    def set_search_zone(self, az_lo: float, az_hi: float,
                         el_lo: float, el_hi: float,
                         range_min: float, range_max: float):
        """设置搜索区（方位为相对法线的偏移量）"""
        with self._lock:
            self.state.search_azimuth_lo_offset = az_lo
            self.state.search_azimuth_hi_offset = az_hi
            self.state.search_elevation_lo = el_lo
            self.state.search_elevation_hi = el_hi
            self.state.search_range_min_m = range_min
            self.state.search_range_max_m = range_max
            self.state.search_zone_set = True

    def set_highlight(self, target_ids: List[int]):
        """设置高亮目标"""
        with self._lock:
            self.state.highlighted_ids = target_ids
            for t in self.targets:
                t.highlighted = t.id in target_ids

    def set_target_count(self, count: int):
        """设置目标数量"""
        with self._lock:
            if 1 <= count <= 20:
                self.targets = create_targets(count)
                # 重置雷达状态
                for t in self.targets:
                    t.highlighted = t.id in self.state.highlighted_ids


    def tas_engage(self, target_id: int, data_rate: int) -> tuple[bool, str]:
        """对目标启动TAS跟踪。返回 (ok, error_msg)。"""
        # 1. 必须在停转模式
        if self.state.mode != "stop":
            return False, "TAS跟踪只能在停转模式下使用"
        # 2. 目标必须存在
        t = next((t for t in self.targets if t.id == target_id), None)
        if t is None:
            return False, f"目标 #{target_id} 不存在"
        # 3. 目标必须已起批（TWS跟踪中）
        if not t.tracked:
            return False, f"目标 #{target_id} 尚未起批，无法进入TAS跟踪"
        # 4. 目标必须在探测范围内（方位±60°、俯仰-5°~70°、距离5~450km）
        az_diff = abs(self._normalize_angle(t.azimuth_deg - self.state.steer_azimuth_deg))
        if az_diff > 60:
            return False, f"目标 #{target_id} 不在方位探测范围（±60°）内"
        if not (-5 <= t.elevation_deg <= 70):
            return False, f"目标 #{target_id} 不在俯仰探测范围（-5°~70°）内"
        if not (5e3 <= t.distance_m <= 450e3):
            return False, f"目标 #{target_id} 不在距离探测范围（5~450km）内"
        # 5. 总数限制：最多10个TAS目标
        if len(self._tas_tracking) >= 10:
            return False, "TAS跟踪目标已达上限（10个）"
        # 6. 10Hz限制：最多10个目标可设10Hz
        if data_rate == 10:
            count_10hz = sum(1 for r in self._tas_tracking.values() if r == 10)
            if count_10hz >= 10:
                return False, "10Hz数据率目标已达上限（10个）"
        self._tas_tracking[target_id] = data_rate
        self._tas_last_updates[target_id] = -999.0  # 立即可检测
        return True, ""

    def tas_disengage(self, target_id: int) -> tuple[bool, str]:
        """取消目标的TAS跟踪，目标将恢复为搜索区TWS检测。返回 (ok, error_msg)。"""
        if target_id not in self._tas_tracking:
            return False, f"目标 #{target_id} 不在TAS跟踪中"
        self._tas_tracking.pop(target_id, None)
        self._tas_last_updates.pop(target_id, None)
        return True, ""

    def reset_targets(self):
        """重置仿真时间和所有目标的跟踪和识别状态（保留目标数量和初始参数）"""
        self._sim_time = 0.0
        self._last_update = time.time()  # 重置时间基准，避免重置后第一帧dt过大
        for t in self.targets:
            t.tracked = False
            t.detected = False
            t.identified_model = None
            t.pending_identification = None
            t.highlighted = False
            t.detection_window.clear()
            t._detection_points.clear()
            t.last_detection_distance_m = 0.0
            t.last_detection_azimuth_deg = 0.0
            t.last_detection_time = 0.0
            t._first_detect_time = -1.0
            t._detect_count = 0
            t._detect_periods = 0
            t._in_beam_last = False

    def get_state_snapshot(self) -> Dict[str, Any]:
        """获取雷达状态快照"""
        with self._lock:
            s = self.state
            return {
                "sim_time": self._sim_time,
                "power": s.power,
                "mode": s.mode,
                "antenna_angle_deg": s.antenna_angle_deg,
                "spin_rate_rpm": s.spin_rate_rpm,
                "steer_azimuth_deg": s.steer_azimuth_deg,
                "steer_elevation_deg": s.steer_elevation_deg,
                "search_zone": {
                    "azimuth": [s.search_azimuth_lo_offset, s.search_azimuth_hi_offset],
                    "elevation": [s.search_elevation_lo, s.search_elevation_hi],
                    "range_m": [s.search_range_min_m, s.search_range_max_m],
                },
                "search_zone_set": s.search_zone_set,
                "targets": [
                    {
                        "id": t.id,
                        "model": t.model,
                        "distance_m": t.distance_m,
                        "azimuth_deg": t.azimuth_deg,
                        "elevation_deg": t.elevation_deg,
                        "height_m": t.height_m,
                        "speed_mps": t.speed_mps,
                        "heading_deg": t.heading_deg,
                        "detected": t.detected,
                        "tracked": t.tracked,
                        "highlighted": t.highlighted,
                        "identified_model": t.identified_model,
                        "pending_identification": t.pending_identification,
                        "detection_window": list(t.detection_window),
                        "last_detection_distance_m": t.last_detection_distance_m,
                        "last_detection_azimuth_deg": t.last_detection_azimuth_deg,
                        "detection_points": list(t._detection_points),
                    }
                    for t in self.targets
                ],
                "highlighted_ids": s.highlighted_ids,
                "tas_tracking": dict(self._tas_tracking),  # {target_id: data_rate}
            }


# 全局单例
_simulator: Optional[RadarSimulator] = None


def get_simulator() -> RadarSimulator:
    global _simulator
    if _simulator is None:
        _simulator = RadarSimulator(target_count=5)
        _simulator.start()
    return _simulator
