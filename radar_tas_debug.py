import requests
import time
BASE = "http://localhost:8000"

# Reset and setup
requests.post(f"{BASE}/api/simulation/reset", timeout=5)
requests.post(f"{BASE}/api/power", json={"state": "on"}, timeout=5)
requests.post(f"{BASE}/api/mode", json={"mode": "spin"}, timeout=5)
time.sleep(10)

# Check targets
s = requests.get(f"{BASE}/api/state", timeout=5).json()
tracked = [t for t in s["targets"] if t.get("tracked")]
print(f"起批目标: {len(tracked)}")
for t in tracked:
    print(f"  #{t['id']} {t['model']} az={t['azimuth_deg']:.1f} el={t['elevation_deg']:.1f} dist={t['distance_m']/1000:.0f}km tracked={t.get('tracked')}")

# Stop
r_stop = requests.post(f"{BASE}/api/mode", json={"mode": "stop"}, timeout=5)
print(f"\n停转: {r_stop.json()}")

# Check steer before
s2 = requests.get(f"{BASE}/api/state", timeout=5).json()
print(f"停转后 state: mode={s2['mode']} steer_azimuth={s2.get('steer_azimuth_deg')} antenna_angle={s2['antenna_angle_deg']}")

# Steer to target 1's azimuth
t1_az = next((t["azimuth_deg"] for t in s["targets"] if t["id"]==1), None)
print(f"\n1号目标方位: {t1_az:.1f}度")
r_steer = requests.post(f"{BASE}/api/steer", json={"azimuth": t1_az, "elevation": 0}, timeout=5)
print(f"steer结果: {r_steer.json()}")

# Check state after steer
s3 = requests.get(f"{BASE}/api/state", timeout=5).json()
print(f"steer后: steer_azimuth={s3.get('steer_azimuth_deg')} antenna_angle={s3['antenna_angle_deg']}")

# Try tas_engage
r_tas = requests.post(f"{BASE}/api/tasEngage", json={"target_id": 1, "data_rate": 1}, timeout=5)
print(f"\ntasEngage: {r_tas.json()}")

# Final state
s4 = requests.get(f"{BASE}/api/state", timeout=5).json()
print(f"tas_tracking: {s4.get('tas_tracking')}")
