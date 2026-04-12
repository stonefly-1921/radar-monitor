import requests
import time
BASE = "http://localhost:8000"
requests.post(f"{BASE}/api/simulation/reset", timeout=5)
requests.post(f"{BASE}/api/power", json={"state": "on"}, timeout=5)
requests.post(f"{BASE}/api/mode", json={"mode": "spin"}, timeout=5)
time.sleep(10)
s = requests.get(f"{BASE}/api/state", timeout=5).json()
tracked = [t for t in s["targets"] if t.get("tracked")]
print(f"起批: {len(tracked)} 目标")
for t in tracked:
    print(f"  #{t['id']} {t['model']} az={t['azimuth_deg']:.1f} dist={t['distance_m']/1000:.0f}km")

# Test: 直接API停转+tas_engage
requests.post(f"{BASE}/api/mode", json={"mode": "stop"}, timeout=5)
requests.post(f"{BASE}/api/steer", json={"azimuth": 79.0}, timeout=5)
r = requests.post(f"{BASE}/api/tasEngage", json={"target_id": 1, "data_rate": 1}, timeout=5)
print(f"\ntasEngage API: {r.json()}")
s2 = requests.get(f"{BASE}/api/state", timeout=5).json()
print(f"tas_tracking: {s2.get('tas_tracking')}")
print(f"mode: {s2['mode']}")
