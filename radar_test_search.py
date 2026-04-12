import requests
import time
import subprocess
import sys

BASE = "http://localhost:8000"

def s():
    r = requests.get(f"{BASE}/api/state", timeout=5).json()
    detected = len([t for t in r["targets"] if t.get("detected")])
    tracked = len([t for t in r["targets"] if t.get("tracked")])
    return r, detected, tracked

# Kill any existing servers
subprocess.run(["powershell", "-Command", 
    "Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }"],
    capture_output=True)
time.sleep(2)

# Start server
proc = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"],
    cwd=r"E:\radar-brain-github\backend",
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
)
time.sleep(5)
try:
    r = requests.get(f"{BASE}/api/state", timeout=5)
    print(f"服务器就绪")
except:
    print(proc.stdout.read1(2000).decode(errors="replace"))
    sys.exit(1)

# 开机+设搜索扇区0-360+转动
requests.post(f"{BASE}/api/simulation/reset", timeout=5)
requests.post(f"{BASE}/api/power", json={"state": "on"}, timeout=5)
requests.post(f"{BASE}/api/search_zone", json={
    "azimuth_lo": -180, "azimuth_hi": 180,
    "elevation_lo": -5, "elevation_hi": 70,
    "range_min": 5000, "range_max": 450000
}, timeout=5)
requests.post(f"{BASE}/api/mode", json={"mode": "spin"}, timeout=5)

st0, d0, t0 = s()
print(f"初始: 检测={d0} 起批={t0}")

# 检查目标位置
print("目标位置:")
for tgt in st0["targets"]:
    print(f"  #{tgt['id']} {tgt['model']} az={tgt['azimuth_deg']:.1f} el={tgt['elevation_deg']:.1f} dist={tgt['distance_m']/1000:.0f}km")

# 轮询检测状态
for i in range(20):
    time.sleep(3)
    st, d, t = s()
    if d > 0 or t > 0:
        print(f"{3*(i+1)}秒: 检测={d} 起批={t} ← 首次发现!")
        for tgt in st["targets"]:
            if tgt.get("detected") or tgt.get("tracked"):
                print(f"  #{tgt['id']} {tgt['model']} tracked={tgt.get('tracked')} detected={tgt.get('detected')}")
        break
    print(f"{3*(i+1)}秒: 检测={d} 起批={t}")

print("\n完成")
proc.terminate()
proc.wait(timeout=5)
