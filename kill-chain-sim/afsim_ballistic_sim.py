"""
AFSIM FiresPath 一阶阻力弹道模型
北京(39.9°N, 116.4°E) → 台北(25.0°N, 121.5°E) 弹道导弹仿真

AFSIM 弹道模型核心公式（来自 FiresPath.cpp UpdateState）:
  vx = v0x * exp(-dt/tc)
  vz = v0z * exp(-dt/tc) - tc*g*(1-exp(-dt/tc))
  x  = tc * v0x * (1-exp(-dt/tc))
  z  = -tc*g*dt + tc*(v0z+tc*g)*(1-exp(-dt/tc))
落地条件: z=0
"""
import math

g = 9.81  # 重力加速度 m/s^2

# Haversine 公式计算大圆距离
def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0  # km
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return 2 * R * math.asin(math.sqrt(a))

range_km = haversine_km(39.9, 116.4, 25.0, 121.5)
Range = range_km * 1000.0  # 米

print("=" * 60)
print("北京 -> 台北 弹道导弹 AFSIM 仿真")
print("=" * 60)
print(f"射程：{range_km:.0f} km (大圆距离)")
print()

def firespath_state(v0x, v0z, tc, dt):
    """给定初始速度和 tc，计算 dt 后的状态"""
    term2 = math.exp(-dt / tc)
    term3 = 1.0 - term2
    vx = v0x * term2
    vz = v0z * term2 - tc * g * term3
    x = tc * v0x * term3
    z = -tc * g * dt + tc * (v0z + tc * g) * term3
    return vx, vz, x, z

def find_impact_time(v0x, v0z, tc, Range, max_dt=600):
    """找落地时间（二分法，z 从正变负的瞬间）"""
    # 先找到 z<0 的时间上界
    dt_hi = 10.0
    vx, vz, x, z = firespath_state(v0x, v0z, tc, dt_hi)
    while z > 0 and dt_hi < max_dt:
        dt_hi *= 2
        vx, vz, x, z = firespath_state(v0x, v0z, tc, dt_hi)
        if dt_hi >= max_dt:
            return None, None, None, None

    dt_lo = 0.0
    for _ in range(100):
        dt = (dt_lo + dt_hi) / 2.0
        vx, vz, x, z = firespath_state(v0x, v0z, tc, dt)
        if z > 0:
            dt_lo = dt
        else:
            dt_hi = dt
    dt = (dt_lo + dt_hi) / 2.0
    vx, vz, x, z = firespath_state(v0x, v0z, tc, dt)
    return dt, vx, vz, x

def find_tc_for_height(target_h_max, elev_deg, Range, tc_guess=100.0):
    """给定目标最大弹道高，二分搜索 tc（cMAX_ORD_TOF 模式）"""
    elev = math.radians(elev_deg)

    def max_height(tc):
        # 用 tc 和 elev 求落地时间和 v0
        dt, _, _, _ = solve_given_elev_and_tc(elev, tc, Range)
        if dt is None:
            return 0.0, 0.0, 0.0
        v0x = Range / (tc * (1.0 - math.exp(-dt / tc)))
        v0z = v0x * math.tan(elev)
        # 找最大高度（vz=0 时）
        # 数值搜索
        dt_lo, dt_hi = 0.01, dt
        for _ in range(100):
            tm = (dt_lo + dt_hi) / 2.0
            _, vz, _, _ = firespath_state(v0x, v0z, tc, tm)
            if vz < 0:
                dt_hi = tm
            else:
                dt_lo = tm
        t_apogee = (dt_lo + dt_hi) / 2.0
        _, vz, _, z = firespath_state(v0x, v0z, tc, t_apogee)
        return max(0.0, z), t_apogee, dt

    def solve_given_elev_and_tc(elev, tc, R):
        # 用数值法：给定 elev 和 tc，求 dt
        for dt_try in range(10, 600):
            term1 = 1.0 - math.exp(-dt_try / tc)
            v0x_val = R / (tc * term1)
            v0z_val = v0x_val * math.tan(elev)
            z = -tc * g * dt_try + tc * (v0z_val + tc * g) * term1
            if z <= 0:
                return dt_try, v0x_val, v0z_val, v0x_val / math.cos(elev)
        return None, None, None, None

    # 二分搜索 tc
    tc_lo, tc_hi = 10.0, 500.0
    for _ in range(100):
        tc_mid = (tc_lo + tc_hi) / 2.0
        h, _, _ = max_height(tc_mid)
        if h < target_h_max:
            tc_lo = tc_mid
        else:
            tc_hi = tc_mid

    tc_final = (tc_lo + tc_hi) / 2.0
    h, t_apogee, dt = max_height(tc_final)
    dt, v0x, v0z, v0 = solve_given_elev_and_tc(elev, tc_final, Range)
    return tc_final, dt, v0, v0x, v0z, h, t_apogee

def solve_given_elev_and_tc(elev, tc, R):
    """给定射角和 tc，求 dt 和 v0"""
    for dt_try in range(10, 600):
        term1 = 1.0 - math.exp(-dt_try / tc)
        v0x = R / (tc * term1)
        v0z = v0x * math.tan(elev)
        z = -tc * g * dt_try + tc * (v0z + tc * g) * term1
        if z <= 0:
            v0 = v0x / math.cos(elev)
            return dt_try, v0x, v0z, v0
    return None, None, None, None

# ============================================================
# 模式1：cELEVATION_TOF（固定射角，查落地时间）
# ============================================================
elev_deg = 45.0
tc1 = 100.0
dt1, v0x1, v0z1, v0_1 = solve_given_elev_and_tc(math.radians(elev_deg), tc1, Range)
print(f"[模式1] cELEVATION_TOF: 射角={elev_deg}deg, tc={tc1}s")
if dt1:
    h1, t_ap1, _ = find_tc_for_height(200000, elev_deg, Range, tc1)
    print(f"  落地时间: {dt1}s ({dt1/60:.2f} min)")
    print(f"  初速 v0: {v0_1:.1f} m/s ({v0_1/1000:.3f} km/s)")
    # 最大高度
    dt_lo, dt_hi = 0.01, dt1
    for _ in range(100):
        tm = (dt_lo + dt_hi) / 2.0
        _, vz, _, _ = firespath_state(v0x1, v0z1, tc1, tm)
        if vz < 0: dt_hi = tm
        else: dt_lo = tm
    t_ap1 = (dt_lo + dt_hi) / 2.0
    _, _, _, h_ap1 = firespath_state(v0x1, v0z1, tc1, t_ap1)
    print(f"  最大弹道高: {h_ap1/1000:.1f} km (at t={t_ap1:.1f}s)")
print()

# ============================================================
# 模式2：cMAX_ORD_TOF（固定最大弹道高 ~100km，求 tc）
# ============================================================
elev_deg2 = 42.0
tc2, dt2, v0_2, v0x2, v0z2, h2, t_ap2 = find_tc_for_height(100000, elev_deg2, Range)
print(f"[模式2] cMAX_ORD_TOF: 目标最大弹道高=100km, 射角={elev_deg2}deg")
if tc2:
    print(f"  time_constant (弹道系数): {tc2:.1f} s")
    print(f"  落地时间: {dt2}s ({dt2/60:.2f} min)")
    print(f"  初速 v0: {v0_2:.1f} m/s ({v0_2/1000:.3f} km/s)")
    print(f"  最大弹道高: {h2/1000:.1f} km (at t={t_ap2:.1f}s)")
print()

# ============================================================
# 模式3：cSIMPLE（简化抛物线，用减小重力模拟阻力）
# ============================================================
print("[模式3] cSIMPLE: 简化抛物线 (g'=7.0 m/s2 等效阻力)")
g_simple = 7.0
# 简化：v0z = g'*t/2, v0x = R/t, h_max = v0z^2/(2*g')
# 从 h_max=100km 求 t: t = sqrt(2*h/g')
t_simple = math.sqrt(2 * 100000 / g_simple)
v0z_simple = g_simple * t_simple / 2.0
v0x_simple = Range / t_simple
v0_simple = math.sqrt(v0z_simple**2 + v0x_simple**2)
elev_simple = math.degrees(math.atan2(v0z_simple, v0x_simple))
print(f"  落地时间: {t_simple:.1f}s ({t_simple/60:.2f} min)")
print(f"  初速 v0: {v0_simple:.1f} m/s ({v0_simple/1000:.3f} km/s)")
print(f"  射角: {elev_simple:.1f}deg")
print(f"  最大弹道高: {100.0} km")
print()

print("=" * 60)
print("【结论】北京->台北(约1730km)弹道导弹 AFSIM 仿真结果")
print("=" * 60)
print(f"射程: {range_km:.0f} km")
print(f"模式2 (cMAX_ORD_TOF) 结果:")
print(f"  弹道系数 tc: {tc2:.1f} s")
print(f"  射角: {elev_deg2}deg")
print(f"  初速: {v0_2:.1f} m/s = {v0_2/1000:.3f} km/s ({v0_2/343:.1f} 马赫)")
print(f"  飞行时间: {dt2}s ({dt2/60:.2f} min)")
print(f"  最大弹道高: {h2/1000:.1f} km")
print()
print("AFSIM FiresPath 弹道计算在 Python 侧完成，")
print("AFSIM 只负责通过 DIS Fire PDU 接收发射指令和交战评估。")
print("=" * 60)