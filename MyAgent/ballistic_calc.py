import math

# ============================================================
# AFSIM FiresPath.cpp 弹道计算 - 北京到台北
# 一阶阻力模型
# ============================================================

g  = 9.80665       # m/s² 重力加速度
tc = 300.0         # s   时间常数（阻力时间常数）
E  = math.radians(45)  # 射角 45°

# --- 地理参数 ---
# 北京
lat0, lon0 = math.radians(39.9), math.radians(116.4)
# 台北
lat1, lon1 = math.radians(25.0), math.radians(121.5)

# Haversine 大圆距离
R  = 6371000       # Earth radius m
dlat = lat1 - lat0
dlon = lon1 - lon0
a  = math.sin(dlat/2)**2 + math.cos(lat0)*math.cos(lat1)*math.sin(dlon/2)**2
c  = 2*math.asin(math.sqrt(a))
S  = R * c         # 大圆弧长 (m)

# 方位角
y  = math.sin(dlon)*math.cos(lat1)
x  = math.cos(lat0)*math.sin(lat1) - math.sin(lat0)*math.cos(lat1)*math.cos(dlon)
bear = math.atan2(y, x)
CosB = math.cos(bear)
SinB = math.sin(bear)

print("="*60)
print("   AFSIM 2.9.0 弹道导弹仿真 - 北京到台北")
print("="*60)
print(f"\n【地理数据】")
print(f"  起点：北京  39.9 N, 116.4 E  (lat0={math.degrees(lat0):.4f}, lon0={math.degrees(lon0):.4f})")
print(f"  终点：台北  25.0 N, 121.5 E  (lat1={math.degrees(lat1):.4f}, lon1={math.degrees(lon1):.4f})")
print(f"  大圆距离 S = {S*1e-3:.2f} km  ({S:.1f} m)")
print(f"  方位角 theta  = {math.degrees(bear):.2f} degrees")

# ============================================================
# 一阶阻力模型（从 FiresPath.cpp UpdateState 提取）
#   vx = v0x * exp(-dt/tc)
#   vz = v0z * exp(-dt/tc) - tc*g*(1-exp(-dt/tc))
#   x  = tc*v0x*(1-exp(-dt/tc))
#   z  = -tc*g*dt + tc*(v0z+tc*g)*(1-exp(-dt/tc))
#
# 落地条件: z = 0, x = S
# 需反解 v0x, v0z, t_f
# ============================================================

# 解析解（来自源码头文件注释 / ComputeInitialVelocity）：
# v0x = S / (tc * (1 - exp(-t_f/tc)))
# v0z = (g*t_f)/(1-exp(-t_f/tc)) - tc*g  (假设无高差 aDeltaAlt=0)
#
# 由 射角45°:  v0x = v0z (45° 意味着 vx=vz 初速分量相等)

# 数值求解 t_f（飞行时间）
def residual(t_f):
    if t_f <= 0:
        return 1e12
    exp_term = math.exp(-t_f / tc)
    term1    = 1.0 - exp_term
    v0x_val  = S / (tc * term1)
    v0z_val  = g * t_f / term1 - tc * g   # deltaAlt=0
    # 射角 45° => v0x = v0z
    return (v0x_val - v0z_val)**2

# 扫描 t_f 找最优值
best_t, best_res = 1000.0, 1e12
for t_guess in range(50, 3000, 1):
    r = residual(float(t_guess))
    if r < best_res:
        best_res = r
        best_t   = float(t_guess)

t_f = best_t
exp_term = math.exp(-t_f / tc)
term1    = 1.0 - exp_term

v0x_val = S / (tc * term1)
v0z_val = g * t_f / term1 - tc * g
v0      = math.sqrt(v0x_val**2 + v0z_val**2)

print(f"\n【弹道模型参数】")
print(f"  重力 g   = {g} m/s^2")
print(f"  时间常数 tc = {tc} s")
print(f"  射角     = 45 degrees")
print(f"  阻力模型 = 一阶指数阻力 (FiresPath.cpp UpdateState)")

print(f"\n【求解结果】")
print(f"  飞行时间 t_f = {t_f:.2f} s = {t_f/60:.2f} min")
print(f"  初速 v0   = {v0:.2f} m/s = {v0/1000*3600:.2f} km/h")
print(f"  v0x       = {v0x_val:.2f} m/s")
print(f"  v0z       = {v0z_val:.2f} m/s")
print(f"  v0x/v0z   = {v0x_val/v0z_val:.4f}  (should be ~1.0 for 45 deg)")

# 最大弹道高：令 dz/dt=0 求 t_apex
# vz = v0z*exp(-t/tc) - tc*g*(1-exp(-t/tc)) = 0
# => (v0z+tc*g)*exp(-t/tc) = tc*g
# => t_apex = tc * ln((v0z+tc*g)/(tc*g))
t_apex = tc * math.log((v0z_val + tc*g) / (tc*g))
exp_apex = math.exp(-t_apex / tc)
z_apex   = -tc*g*t_apex + tc*(v0z_val+tc*g)*(1-exp_apex)
x_apex   = tc*v0x_val*(1-exp_apex)

print(f"\n【弹道要素】")
print(f"  射程       = {S*1e-3:.2f} km")
print(f"  飞行时间   = {t_f:.2f} s ({t_f/60:.2f} min)")
print(f"  理论初速   = {v0:.2f} m/s ({v0/1000*3600:.2f} km/h)")
print(f"  最大弹道高 = {z_apex:.2f} m = {z_apex/1000:.2f} km")
print(f"  最高点时刻 = {t_apex:.2f} s ({t_apex/60:.2f} min)")
print(f"  最高点水平 = {x_apex:.2f} m = {x_apex/1000:.2f} km (from launch)")

# 时间节点采样
print(f"\n【弹道剖面 - 时间采样】")
print(f"{'t(s)':>8} {'x(m)':>10} {'z(m)':>10} {'vx(m/s)':>10} {'vz(m/s)':>10}")
print("-"*52)
for pct in [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]:
    t_pts = t_f * pct / 100.0
    exp_t = math.exp(-t_pts / tc)
    trm   = 1.0 - exp_t
    vx_pt = v0x_val * exp_t
    vz_pt = v0z_val * exp_t - tc*g*trm
    x_pt  = tc*v0x_val*trm
    z_pt  = -tc*g*t_pts + tc*(v0z_val+tc*g)*trm
    print(f"{t_pts:>8.1f} {x_pt:>10.1f} {z_pt:>10.1f} {vx_pt:>10.2f} {vz_pt:>10.2f}")

print("\n" + "="*60)
print("  计算完成 - 基于 AFSIM FiresPath.cpp 解析模型")
print("="*60)