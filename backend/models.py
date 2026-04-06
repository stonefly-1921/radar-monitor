"""
雷达仿真 - 数据模型
"""
import math
import random
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

@dataclass
class Target:
    id: int
    model: str
    
    distance_m: float
    azimuth_deg: float
    elevation_deg: float
    height_m: float
    
    speed_mps: float
    heading_deg: float
    turn_rate_rps: float
    
    center_x_m: float
    center_y_m: float
    orbit_radius_m: float
    
    # 跑道模型字段
    maneuver_type: str = "runway"
    runway_center_azimuth_deg: float = 0.0
    runway_length_m: float = 100e3
    runway_width_m: float = 30e3
    runway_progress: float = 0.0
    runway_center_distance_m: float = 200e3  # 跑道中心到雷达的距离
    
    detected: bool = False
    tracked: bool = False
    highlighted: bool = False
    identified_model: Optional[str] = None  # 识别后赋值，None=未识别
    pending_identification: Optional[str] = None  # 点识别时设置，下次检测到目标时生效
    detection_window: List[bool] = field(default_factory=list)
    last_detection_distance_m: float = 0.0
    last_detection_azimuth_deg: float = 0.0
    last_detection_time: float = 0.0
    # 停转模式起批专用
    _first_detect_time: float = -1.0
    _detect_periods: int = 0
    _detect_count: int = 0
    _in_beam_last: bool = False  # 上帧是否在波束内（防止spin模式同一目标重复计数）
    # 检测点历史 [{time, azimuth_deg, distance_m}] 用于前端显示
    _detection_points: List[Dict[str, Any]] = field(default_factory=list)
    
    def update(self, dt_seconds: float):
        if self.maneuver_type == "runway":
            # 跑道来回模型：单车道连续运动
            # _runway_progress 0→1→0 来回，direction 控制方向
            if not hasattr(self, '_runway_progress'):
                self._runway_progress = 0.0  # 0=跑道起点, 1=跑道终点
                self._runway_direction = 1   # +1=正向(起点→终点), -1=反向(终点→起点)
            
            # 速度换算：每秒走的progress
            delta_progress = (self.speed_mps / (self.runway_length_m * 2)) * dt_seconds
            self._runway_progress += delta_progress * self._runway_direction
            
            # 碰到端点反向（无跳变）
            if self._runway_progress >= 1.0:
                self._runway_progress = 1.0
                self._runway_direction = -1
            elif self._runway_progress <= 0.0:
                self._runway_progress = 0.0
                self._runway_direction = 1
            
            # 沿跑道位置：0→1 映射到 -length/2 → +length/2（连续无跳变）
            along = (self._runway_progress * 2 - 1) * self.runway_length_m / 2
            
            # 跑道中心点的XY（以雷达为原点）
            rad_az = math.radians(self.runway_center_azimuth_deg)
            cx = self.runway_center_distance_m * math.sin(rad_az)
            cy = self.runway_center_distance_m * math.cos(rad_az)
            # 目标位置（沿跑道中心线，无lateral跳变）
            dx = along * math.cos(rad_az)
            dy = along * math.sin(rad_az)
            x = cx + dx
            y = cy + dy
            
            self.distance_m = math.sqrt(x**2 + y**2 + self.height_m**2)
            self.azimuth_deg = math.degrees(math.atan2(y, x))
            self.elevation_deg = math.degrees(math.atan2(self.height_m, math.sqrt(x**2 + y**2)))
            
            # 航向：沿跑道运动方向（连续，无180°跳变）
            # 正向时 heading = runway_center_azimuth_deg，反向时 +180°
            self.heading_deg = (self.runway_center_azimuth_deg + (1 - self._runway_direction) * 180) % 360
        else:
            # 原有圆弧巡逻模型
            omega = self.speed_mps / self.orbit_radius_m if self.orbit_radius_m > 0 else 0
            self.heading_deg += math.degrees(omega * dt_seconds)
            rad_heading = math.radians(self.heading_deg)
            dx = self.center_x_m + self.orbit_radius_m * math.cos(rad_heading)
            dy = self.center_y_m + self.orbit_radius_m * math.sin(rad_heading)
            self.distance_m = math.sqrt(dx**2 + dy**2)
            self.azimuth_deg = math.degrees(math.atan2(dy, dx))
            self.elevation_deg = math.degrees(math.atan2(self.height_m, math.sqrt(dx**2 + dy**2)))

@dataclass  
class RadarState:
    power: bool = False
    mode: str = "stop"
    antenna_angle_deg: float = 0.0
    spin_rate_rpm: float = 6.0
    steer_azimuth_deg: float = 0.0
    steer_elevation_deg: float = 0.0
    # 停转模式搜索区偏移（相对法线方位）
    search_azimuth_lo_offset: float = -60.0
    search_azimuth_hi_offset: float = 60.0
    # 停转模式：搜索区扫描状态
    scan_position_deg: float = 0.0
    scan_start_time: float = 0.0
    search_azimuth_lo: float = -60.0
    search_azimuth_hi: float = 60.0
    search_elevation_lo: float = -5.0
    search_elevation_hi: float = 70.0
    search_range_min_m: float = 5000.0
    search_range_max_m: float = 450000.0
    search_zone_set: bool = False   # 停转模式搜索区是否已配置（未配置时非TAS目标不检测）
    highlighted_ids: List[int] = field(default_factory=list)
    beamwidth_az_deg: float = 2.0   # TAS波束宽度（方位）
    beamwidth_el_deg: float = 2.0   # TAS波束宽度（俯仰）
    search_zone_set: bool = False    # 是否已设置搜索区

def create_targets(count: int, seed: int = 42) -> List[Target]:
    if seed:
        random.seed(seed)
    models = ["F35", "F22", "J20", "Su57", "B2", "J-16", "F-15", "Eurofighter", "Rafale", "F-18"]
    targets = []
    for i in range(count):
        # 跑道中心：方位0-360°均匀，中心距离5-450km
        runway_center_azimuth_deg = (360.0 / count) * i + random.uniform(-10, 10)
        runway_center_distance_m = random.uniform(50e3, 400e3)  # 中心距雷达50-400km
        runway_length_m = random.uniform(50e3, 200e3)  # 跑道长度
        runway_width_m = random.uniform(20e3, 50e3)  # 跑道宽度
        runway_progress = random.uniform(0.0, 1.0)
        height_m = random.uniform(6000, 12000)
        speed = random.uniform(300, 500)
        
        # 初始航向基于 progress 方向
        if runway_progress < 0.5:
            heading = runway_center_azimuth_deg
        else:
            heading = (runway_center_azimuth_deg + 180) % 360
        
        # 初始位置计算：以跑道中心为基准，沿 runway_direction ± length/2 往返
        phase = runway_progress * 2 * math.pi
        along = math.sin(phase) * runway_length_m / 2  # -length/2 到 +length/2 往返
        if runway_progress < 0.5:
            perp_offset = -runway_width_m / 2  # segment A
        else:
            perp_offset = runway_width_m / 2  # segment B
        
        rad_az = math.radians(runway_center_azimuth_deg)
        rad_perp = math.radians(runway_center_azimuth_deg + 90)
        # 跑道中心点的XY（以雷达为原点）
        cx = runway_center_distance_m * math.sin(rad_az)
        cy = runway_center_distance_m * math.cos(rad_az)
        # 目标相对跑道中心的偏移
        dx = along * math.cos(rad_az) + perp_offset * math.cos(rad_perp)
        dy = along * math.sin(rad_az) + perp_offset * math.sin(rad_perp)
        x0 = cx + dx
        y0 = cy + dy
        init_dist = math.sqrt(x0**2 + y0**2 + height_m**2)
        init_az = math.degrees(math.atan2(y0, x0))
        init_el = math.degrees(math.atan2(height_m, math.sqrt(x0**2 + y0**2)))
        
        targets.append(Target(
            id=i+1, model=models[i % len(models)],
            distance_m=init_dist, azimuth_deg=init_az, elevation_deg=init_el, height_m=height_m,
            speed_mps=speed, heading_deg=heading, turn_rate_rps=0,
            center_x_m=0.0, center_y_m=0.0, orbit_radius_m=0.0,
            maneuver_type="runway",
            runway_center_azimuth_deg=runway_center_azimuth_deg,
            runway_length_m=runway_length_m,
            runway_width_m=runway_width_m,
            runway_progress=runway_progress,
        ))
    return targets
