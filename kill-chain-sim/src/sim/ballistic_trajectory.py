#!/usr/bin/env python3
"""
北京 → 台北 弹道导弹攻击仿真
AFSIM FiresPath 一阶阻力弹道模型 Python 实现

AFSIM 弹道方程 (FiresPath.cpp, UpdateState):
  vx(t) = v0x * exp(-t/τ)
  vz(t) = v0z * exp(-t/τ) - τ*g*(1 - exp(-t/τ))
  x(t)  = τ * v0x * (1 - exp(-t/τ))
  z(t)  = -τ*g*t + τ*(v0z + τ*g)*(1 - exp(-t/τ))

τ = mTimeConstant (时间常数, 典型 75-100s for SRBM)
"""

import math
from dataclasses import dataclass

G = 9.80665  # m/s²

# 任务场景
BEIJING_LAT = 39.9
BEIJING_LON = 116.4
TAIPEI_LAT  = 25.0
TAIPEI_LON  = 121.5

# 200km 短程导弹: 发射点取模拟的近距位置
# (北京西偏北约 200km 作为任务射程代表)
# 为贴近任务要求，用 200km 射程代入计算
# 发射点: 北京西约 200km at ~40N
lon_w = 200.0 / (111.32 * math.cos(math.radians(39.9)))
LAUNCH_LAT = 39.9
LAUNCH_LON = 116.4 - lon_w
TARGET_LAT = 25.0
TARGET_LON = 121.5


@dataclass
class TrajectoryResult:
    range_km: float
    firing_angle_deg: float
    initial_speed_mps: float
    time_of_flight_s: float
    max_height_km: float
    time_constant_s: float
    ballistic_coeff: float
    model: str


def haversine_km(lat1, lon1, lat2, lon2):
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
    return 6371.0 * 2 * math.asin(math.sqrt(a))


def bearing_deg(lat1, lon1, lat2, lon2):
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dlam = math.radians(lon2 - lon1)
    x = math.cos(phi2) * math.sin(dlam)
    y = math.cos(phi1)*math.sin(phi2) - math.sin(phi1)*math.cos(phi2)*math.cos(dlam)
    return math.degrees(math.atan2(x, y))


# ────────────────────────────────────────────────────────────────
# AFSIM 弹道状态 (FiresPath.cpp UpdateState)
# ────────────────────────────────────────────────────────────────
def state_at_t(tau, v0x, v0z, t, g=G):
    """弹道状态 at time t"""
    e = math.exp(-t / tau)
    vx = v0x * e
    vz = v0z * e - tau * g * (1.0 - e)
    x  = tau * v0x * (1.0 - e)
    z  = -tau * g * t + tau * (v0z + tau * g) * (1.0 - e)
    return x, z, vx, vz


def apogee_time(tau, v0z, g=G):
    """弹道最高点时刻 t_ap = τ * ln(1 + v0z/(gτ))"""
    if v0z <= 0:
        return 0.0
    return tau * math.log1p(v0z / (g * tau))


# ────────────────────────────────────────────────────────────────
# 核心: 直接从射程+弹道高反推射角、初速、τ
#
# AFSIM ComputeTimeConstantFromMaxOrd() 逻辑:
#   输入: 射程 R, 落地时间 tof, 最大弹道高 H_max
#   1. 猜测 τ 初值
#   2. 从射程方程反推 v0x:  R = τ*v0x*(1 - exp(-tof/τ))
#   3. 从弹道高方程反推 v0z:  H_max = ...
#   4. 迭代 τ 直到弹道顶点高度 ≈ H_max
#
# 这里用更直接的解析法:
#   对每个候选 τ，从射程和 tof 解出 v0x
#   从弹道高解出 v0z
#   迭代 τ 直到 apogee height 收敛
# ────────────────────────────────────────────────────────────────

def solve_ballistic_R_H(R_m, tof, H_max, delta_alt=0.0, tau_init=75.0, max_iter=300):
    """
    从射程、飞行时间、最大弹道高 求解 τ, v0x, v0z
    对应 AFSIM ComputeTimeConstantFromMaxOrd()

    方程组:
      (1) R = τ*v0x*(1 - exp(-tof/τ))
      (2) H_max = apogee from (τ, v0z)
      (3) z(tof) = delta_alt  (落地条件)

    先从 (1) 得到 v0x = R / (τ*(1-exp(-tof/τ)))
    然后由 (3) 得到 v0z:
      delta_alt = -τ*g*tof + τ*(v0z+τ*g)*(1-exp(-tof/τ))
      => v0z = [delta_alt/(τ*(1-e)) + g*τ - g*tof] / (1 - e/???) 
      实际上直接用 AFSIM 公式:
      v0z = g*tof/term1 - τ*g + delta_alt/(τ*term1)
      其中 term1 = 1 - exp(-tof/τ)
    """
    tau = tau_init

    for i in range(max_iter):
        e0 = math.exp(-tof / tau)
        e1 = 1.0 - e0
        v0x = R_m / tau / e1
        v0z = G * tof / e1 - tau * G + delta_alt / tau / e1

        ta = apogee_time(tau, v0z, G)
        _, z_ap, _, _ = state_at_t(tau, v0x, v0z, ta, G)
        if z_ap < 0:
            z_ap = 0.0

        delh = H_max - z_ap
        if abs(delh) <= 0.1:
            break

        # AFSIM dzda 敏感性
        term2 = math.exp(-ta / tau)
        term3 = 1.0 - term2
        dzda = ((v0z + 2.0*G*tau)*term3
                - v0z*ta/tau*term2
                - G*ta*(1.0 + term2))
        if abs(dzda) < 1e-10:
            dzda = 1.0
        tau += delh / dzda
        tau = max(10.0, min(500.0, tau))

    # 最终值
    e0 = math.exp(-tof / tau)
    e1 = 1.0 - e0
    v0x = R_m / tau / e1
    v0z = G * tof / e1 - tau * G + delta_alt / tau / e1
    return tau, v0x, v0z


def find_tof_for_given_range(R_m, tau, v0x, v0z, delta_alt=0.0, tof_guess=None, max_iter=100):
    """给定 τ,v0x,v0z，用落地条件 z(tof)=delta_alt 求 tof"""
    if tof_guess is None:
        tof_guess = R_m / v0x * 2.0  # 粗估
    tof = tof_guess
    for _ in range(max_iter):
        _, z, _, _ = state_at_t(tau, v0x, v0z, tof, G)
        if abs(z - delta_alt) < 0.5:
            break
        e = math.exp(-tof / tau)
        vz = v0z * e - tau * G * (1.0 - e)
        dz_dt = -(vz)
        if abs(dz_dt) < 0.01:
            dz_dt = -1.0
        tof -= (z - delta_alt) / dz_dt * 0.5
        tof = max(10.0, tof)
    return tof


def afsim_lookup(range_km, max_h_km):
    """
    模拟 AFSIM 查表法 GetMaxOrdAndTOF
    对于 200km SRBM，用外弹道学近似给出参考射角和飞行时间
    """
    R = range_km * 1000.0
    H = max_h_km * 1000.0

    # 对于 SRBM 射程<1000km，可用标准椭圆弹道近似
    # θ = atan(sqrt(2H/R))  直接从 R,H 求最优射角
    theta = math.atan(math.sqrt(2.0 * H / R))
    v0 = math.sqrt(G * R / math.sin(2.0 * theta))
    tof = 2.0 * v0 * math.sin(theta) / G

    return math.degrees(theta), tof, v0


def solve_ballistic_elevation(R_m, tof, elev_rad, delta_alt=0.0, tau_init=75.0, max_iter=300):
    """
    从射程、飞行时间、落地仰角 求解 τ, v0x, v0z
    对应 AFSIM ComputeTimeConstantFromElevationAngle()
    """
    tau = tau_init
    tanE = math.tan(elev_rad)

    for _ in range(max_iter):
        e0 = math.exp(-tof / tau)
        e1 = 1.0 - e0
        v0z = G * tof / e1 - tau * G + delta_alt / tau / e1
        v0x = v0z / tanE
        impact_R = v0x * tau * e1

        dRdTc = v0x * e1 - v0x * tof / tau * e0
        dR = R_m - impact_R
        if abs(dR) < 0.1:
            break
        if abs(dRdTc) < 1e-10:
            dRdTc = 1.0
        tau += dR / dRdTc
        tau = max(10.0, min(500.0, tau))

    e0 = math.exp(-tof / tau)
    e1 = 1.0 - e0
    v0z = G * tof / e1 - tau * G + delta_alt / tau / e1
    v0x = v0z / tanE
    return tau, v0x, v0z


def compute_srbm(range_km, max_h_km, delta_alt=0.0, method="maxord"):
    """
    主弹道计算函数

    method="maxord": 用射程+弹道高+toflight 迭代求解
    method="elevation": 用射程+射角+toflight 迭代求解
    """
    R_m = range_km * 1000.0
    H_m = max_h_km * 1000.0

    # 查表法初始估计 (提供 tof 初始值)
    elev_deg_lookup, tof_lookup, v0_lookup = afsim_lookup(range_km, max_h_km)
    elev_rad = math.radians(elev_deg_lookup)

    if method == "maxord":
        tau, v0x, v0z = solve_ballistic_R_H(
            R_m, tof_lookup, H_m, delta_alt, tau_init=75.0, max_iter=300)
    else:
        tau, v0x, v0z = solve_ballistic_elevation(
            R_m, tof_lookup, elev_rad, delta_alt, tau_init=75.0, max_iter=300)

    # 精确求解 tof (落地条件)
    tof = find_tof_for_given_range(R_m, tau, v0x, v0z, delta_alt, tof_guess=tof_lookup)

    # 检查 apogee
    ta = apogee_time(tau, v0z, G)
    _, z_ap, _, _ = state_at_t(tau, v0x, v0z, ta, G)
    actual_Hmax = max(z_ap, 0.0)

    v0 = math.sqrt(v0x**2 + v0z**2)
    firing_angle = math.degrees(math.atan2(v0z, v0x))

    return TrajectoryResult(
        range_km=range_km,
        firing_angle_deg=round(firing_angle, 2),
        initial_speed_mps=round(v0, 1),
        time_of_flight_s=round(tof, 1),
        max_height_km=round(actual_Hmax / 1000.0, 2),
        time_constant_s=round(tau, 2),
        ballistic_coeff=round(1.0 / tau, 6),
        model="一阶阻力模型 (AFSIM FiresPath)"
    ), dict(elev_lookup=elev_deg_lookup, tof_lookup=tof_lookup,
            v0_lookup=round(v0_lookup, 1), H_lookup_km=max_h_km)


def main():
    print("=" * 58)
    print("AFSIM FiresPath 弹道模型 Python 实现")
    print("北京 → 台北 弹道导弹攻击仿真")
    print("=" * 58)
    print()

    # 地理
    R_actual = haversine_km(BEIJING_LAT, BEIJING_LON, TAIPEI_LAT, TAIPEI_LON)
    bear_actual = bearing_deg(BEIJING_LAT, BEIJING_LON, TAIPEI_LAT, TAIPEI_LON)
    R_task = haversine_km(LAUNCH_LAT, LAUNCH_LON, TARGET_LAT, TARGET_LON)
    bear_task = bearing_deg(LAUNCH_LAT, LAUNCH_LON, TARGET_LAT, TARGET_LON)

    print(f"[任务场景]")
    print(f"  实际大圆距离: {R_actual:.0f} km  (方位 {bear_actual:.1f} deg)")
    print(f"  任务射程:     {R_task:.0f} km  (方位 {bear_task:.1f} deg)")
    print(f"  发射点: ({LAUNCH_LAT}N, {LAUNCH_LON:.1f}E)")
    print(f"  目标点: ({TARGET_LAT}N, {TARGET_LON}E)")
    print()

    # SRBM 200km 射程典型弹道高 40-80km
    # 取 60km 作为基准弹道
    max_h_km = 60.0
    delta_alt = 0.0

    # ── 一阶阻力模型 ──
    result, table = compute_srbm(R_task, max_h_km, delta_alt, method="maxord")

    # ── AFSIM 查表法 ──
    elev_table = table["elev_lookup"]
    tof_table = table["tof_lookup"]
    v0_table = table["v0_lookup"]
    # 查表弹道高 (简化无阻力公式计算)
    H_table_km = (v0_table**2 * math.sin(math.radians(elev_table))**2
                  / (2.0 * G)) / 1000.0

    print(f"[弹道仿真结果]")
    print(f"  射程:         {result.range_km:.0f} km")
    print(f"  射角:         {result.firing_angle_deg:.2f} deg")
    print(f"  初速:         {result.initial_speed_mps:.1f} m/s")
    print(f"  飞行时间:     {result.time_of_flight_s:.1f} s")
    print(f"  最大弹道高:   {result.max_height_km:.2f} km")
    print(f"  时间常数 τ:   {result.time_constant_s:.2f} s")
    print(f"  弹道系数 1/τ: {result.ballistic_coeff:.6f} (1/s)")
    print(f"  弹道模型:     {result.model}")
    print()

    print(f"[AFSIM 查表法参考]")
    print(f"  射程:         {R_task:.0f} km")
    print(f"  射角:         {elev_table:.2f} deg")
    print(f"  初速:         {v0_table:.1f} m/s")
    print(f"  飞行时间:     {tof_table:.1f} s")
    print(f"  最大弹道高:   {H_table_km:.2f} km")
    print(f"  弹道模型:     查表法 (外弹道预计算表)")
    print()

    # 弹道剖面
    tau = result.time_constant_s
    v0x = result.initial_speed_mps * math.cos(math.radians(result.firing_angle_deg))
    v0z = result.initial_speed_mps * math.sin(math.radians(result.firing_angle_deg))
    tof = result.time_of_flight_s
    ta = apogee_time(tau, v0z, G)

    print(f"[弹道剖面采样]")
    print(f"  {'t(s)':<8} {'Alt(km)':<10} {'v(m/s)':<12} {'vz(m/s)':<10}")
    print(f"  {'-'*8} {'-'*10} {'-'*12} {'-'*10}")
    checkpoints = [0.0, ta*0.25, ta*0.5, ta*0.75, ta,
                   tof*0.6, tof*0.8, tof]
    for t in checkpoints:
        t = min(t, tof - 0.01)
        if t < 0:
            t = 0.0
        _, z, vx, vz = state_at_t(tau, v0x, v0z, t, G)
        speed = math.sqrt(vx**2 + vz**2)
        alt_km = max(z, 0.0) / 1000.0
        print(f"  {t:<8.1f} {alt_km:<10.2f} {speed:<12.1f} {-vz:<10.1f}")

    print()
    print("=" * 58)
    print()
    print("【输出格式】")
    print(f"射程：{result.range_km:.0f} km")
    print(f"射角：{result.firing_angle_deg:.2f} deg")
    print(f"初速：{result.initial_speed_mps:.1f} m/s")
    print(f"飞行时间：{result.time_of_flight_s:.1f} s")
    print(f"最大弹道高：{result.max_height_km:.2f} km")
    print(f"使用的弹道模型：{result.model}")
    print()
    print("【AFSIM 查表法对比】")
    print(f"射程：{R_task:.0f} km")
    print(f"射角：{elev_table:.2f} deg")
    print(f"初速：{v0_table:.1f} m/s")
    print(f"飞行时间：{tof_table:.1f} s")
    print(f"最大弹道高：{H_table_km:.2f} km")
    print(f"使用的弹道模型：查表法")


if __name__ == "__main__":
    main()