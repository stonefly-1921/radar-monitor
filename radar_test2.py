import requests
import time

BASE = "http://localhost:8000"

def s():
    r = requests.get(f"{BASE}/api/state", timeout=5)
    return r.json()

# 开机+转动
requests.post(f"{BASE}/api/power", json={"state": "on"}, timeout=5)
requests.post(f"{BASE}/api/mode", json={"mode": "spin"}, timeout=5)

st = s()
print(f"开机状态: power={st['power']}, mode={st['mode']}, targets={len(st['targets'])}")

# 等待检测
print("等待10秒让目标进入检测窗口...")
time.sleep(10)

st2 = s()
print(f"\n10秒后状态: power={st2['power']}, mode={st2['mode']}")
detected = [t for t in st2['targets'] if t.get('detected')]
tracked = [t for t in st2['targets'] if t.get('tracked')]
print(f"检测到目标: {len(detected)}批")
print(f"起批目标: {len(tracked)}批")
for t in detected:
    print(f"  #{t['id']} {t['model']} az={t['azimuth_deg']:.1f} dist={t['distance_m']/1000:.0f}km tracked={t.get('tracked')} tas={t.get('tas_mode')}")

# 测试跟踪 - 先停转再TAS
print("\n=== 测试：停转+对1号目标TAS ===")
requests.post(f"{BASE}/api/mode", json={"mode": "stop"}, timeout=5)
# 获取1号目标方位
t1 = next((t for t in s()['targets'] if t['id'] == 1), None)
if t1:
    az = t1['azimuth_deg']
    print(f"1号目标方位: {az:.1f}度，设置为停转角度")
    requests.post(f"{BASE}/api/steer", json={"azimuth": az}, timeout=5)
    st3 = s()
    print(f"停转角度: {st3['antenna_angle_deg']}")

r_tas = requests.post(f"{BASE}/api/tasEngage", json={"target_id": 1, "data_rate": 1}, timeout=5)
print(f"TASengage结果: {r_tas.json()}")

st4 = s()
print(f"\nTAS状态: {st4.get('tas_tracking')}")

# 测试数据率调整
print("\n=== 测试：调整数据率为10Hz ===")
r_dr = requests.post(f"{BASE}/api/tasEngage", json={"target_id": 1, "data_rate": 10}, timeout=5)
print(f"调数据率结果: {r_dr.json()}")
st5 = s()
print(f"TAS状态: {st5.get('tas_tracking')}")

# 测试识别
print("\n=== 测试：识别1号目标 ===")
r_id = requests.post(f"{BASE}/api/identify", json={"target_id": 1}, timeout=5)
print(f"识别结果: {r_id.json()}")
st6 = s()
t1_new = next((t for t in st6['targets'] if t['id']==1), None)
print(f"1号目标identified_model: {t1_new.get('identified_model') if t1_new else 'not found'}")

# 测试filter_targets
print("\n=== 测试：过滤F22目标 ===")
r_f = requests.get(f"{BASE}/api/state", timeout=5)
targets = r_f.json()['targets']
f22s = [t for t in targets if 'f22' in t.get('model','').lower() or 'f22' in (t.get('identified_model') or '').lower()]
print(f"F22目标: {[t['id'] for t in f22s]}")

# 测试多目标TAS
print("\n=== 测试：对1+2+3号目标TAS ===")
for tid in [1,2,3]:
    r_m = requests.post(f"{BASE}/api/mode", json={"mode": "stop"}, timeout=5)
    t = next((t for t in s()['targets'] if t['id']==tid), None)
    if t:
        az_t = t['azimuth_deg']
        print(f"#{tid}方位={az_t:.1f}停转")
        requests.post(f"{BASE}/api/steer", json={"azimuth": az_t}, timeout=5)
        r_t = requests.post(f"{BASE}/api/tasEngage", json={"target_id": tid, "data_rate": 1}, timeout=5)
        print(f"  TASengage: {r_t.json()}")

st7 = s()
print(f"最终TAS跟踪: {st7.get('tas_tracking')}")
