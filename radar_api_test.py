import requests
import time
import subprocess
import sys
import os

BASE = "http://localhost:8000"

# Kill any existing servers
os.system("netstat -ano | findstr :8000 | findstr LISTEN > nul 2>&1")
# Use PowerShell to kill
import subprocess
r = subprocess.run(["powershell", "-Command", 
    "Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }"],
    capture_output=True, text=True)
time.sleep(2)

# Start server
print("启动服务器...")
proc = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"],
    cwd=r"E:\radar-brain-github\backend",
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
)
time.sleep(5)

# Verify
try:
    r = requests.get(f"{BASE}/api/state", timeout=5)
    print(f"服务器就绪: power={r.json()['power']}")
except Exception as e:
    print(f"服务器启动失败: {e}")
    print(proc.stdout.read1(2000).decode(errors="replace"))
    sys.exit(1)

def s():
    r = requests.get(f"{BASE}/api/state", timeout=5).json()
    detected = len([t for t in r["targets"] if t.get("detected")])
    tracked = len([t for t in r["targets"] if t.get("tracked")])
    tas = len(r.get("tas_tracking", {}))
    return r, detected, tracked, tas

# Reset
requests.post(f"{BASE}/api/simulation/reset", timeout=5)
print("\n=== 组别一：基础功能 ===")

# 1. 开机+全方位
print("\n[1] 开机+全方位搜索")
requests.post(f"{BASE}/api/power", json={"state": "on"}, timeout=5)
requests.post(f"{BASE}/api/mode", json={"mode": "spin"}, timeout=5)
time.sleep(3)
st, d, t, tas = s()
print(f"  状态: power={st['power']} mode={st['mode']} 检测={d} 起批={t}")

# 等待目标
print("  等待12秒...")
time.sleep(12)
st, d, t, tas = s()
print(f"  12秒后: 检测={d} 起批={t}")
for tgt in st["targets"]:
    if tgt.get("detected"):
        print(f"    #{tgt['id']} {tgt['model']} az={tgt['azimuth_deg']:.0f} dist={tgt['distance_m']/1000:.0f}km")

# 2. 查目标数
print("\n[2] 查目标数（直接状态）")
print(f"  起批={t}")

# 3. TAS在spin应拒绝
print("\n[3] 转动模式TAS（应拒绝）")
r3 = requests.post(f"{BASE}/api/tasEngage", json={"target_id": 1, "data_rate": 1}, timeout=5)
print(f"  tasEngage结果: {r3.json()}")

# 4. 停转+TAS
print("\n[4] 停转+对1号TAS")
requests.post(f"{BASE}/api/mode", json={"mode": "stop"}, timeout=5)
# 取1号目标方位
tgt1 = next((t for t in s()[0]["targets"] if t["id"]==1), None)
if tgt1:
    az1 = tgt1["azimuth_deg"]
    print(f"  1号方位={az1:.1f}度，steer到该方位")
    requests.post(f"{BASE}/api/steer", json={"azimuth": az1, "elevation": 0}, timeout=5)
r4 = requests.post(f"{BASE}/api/tasEngage", json={"target_id": 1, "data_rate": 1}, timeout=5)
print(f"  tasEngage结果: {r4.json()}")
st4, d4, t4, tas4 = s()
print(f"  TAS状态: {st4.get('tas_tracking')}")

# 5. 数据率10Hz
print("\n[5] 数据率调为10Hz")
r5 = requests.post(f"{BASE}/api/tasEngage", json={"target_id": 1, "data_rate": 10}, timeout=5)
print(f"  结果: {r5.json()}")
st5, d5, t5, tas5 = s()
print(f"  TAS: {st5.get('tas_tracking')}")

# 6. 识别
print("\n[6] 识别1号目标")
r6 = requests.post(f"{BASE}/api/identify", json={"target_id": 1}, timeout=5)
print(f"  结果: {r6.json()}")
st6, d6, t6, tas6 = s()
tgt1n = next((t for t in st6["targets"] if t["id"]==1), None)
print(f"  identified_model: {tgt1n.get('identified_model') if tgt1n else 'N/A'}")

# 7. 哪些已识别
print("\n[7] 已识别目标列表")
identified = [(t["id"], t.get("identified_model") or t.get("model")) for t in st6["targets"] if t.get("identified_model")]
print(f"  {identified}")

print("\n=== 组别二：高级功能 ===")
requests.post(f"{BASE}/api/simulation/reset", timeout=5)
requests.post(f"{BASE}/api/power", json={"state": "on"}, timeout=5)
requests.post(f"{BASE}/api/mode", json={"mode": "spin"}, timeout=5)
print("重置+开机，等待目标...")
time.sleep(12)

# 8. 所有目标识别
print("\n[8] 所有目标识别（应先停转）")
st8, d8, t8, tas8 = s()
print(f"  当前: 检测={d8} 起批={t8}")
# 逐个识别所有检测到的目标
for tgt in st8["targets"]:
    if tgt.get("detected"):
        rid = requests.post(f"{BASE}/api/identify", json={"target_id": tgt["id"]}, timeout=5)
        print(f"  识别#{tgt['id']}: {rid.json()}")

# 9. 多目标TAS
print("\n[9] 1+2+3号目标TAS")
for tid in [1,2,3]:
    tgt = next((t for t in s()[0]["targets"] if t["id"]==tid), None)
    if tgt:
        az = tgt["azimuth_deg"]
        requests.post(f"{BASE}/api/mode", json={"mode": "stop"}, timeout=5)
        requests.post(f"{BASE}/api/steer", json={"azimuth": az}, timeout=5)
        r9 = requests.post(f"{BASE}/api/tasEngage", json={"target_id": tid, "data_rate": 1}, timeout=5)
        print(f"  #{tid} az={az:.1f} TAS: {r9.json()}")
st9, d9, t9, tas9 = s()
print(f"  TAS: {st9.get('tas_tracking')}")

# 10. F22 TAS
print("\n[10] F22 TAS")
st10, d10, t10, tas10 = s()
f22 = [t for t in st10["targets"] if "f22" in (t.get("identified_model") or t.get("model") or "").lower()]
print(f"  F22目标: {[(t['id'], t.get("model")) for t in f22]}")
if f22:
    tgt = f22[0]
    az = tgt["azimuth_deg"]
    requests.post(f"{BASE}/api/mode", json={"mode": "stop"}, timeout=5)
    requests.post(f"{BASE}/api/steer", json={"azimuth": az}, timeout=5)
    r10 = requests.post(f"{BASE}/api/tasEngage", json={"target_id": tgt["id"], "data_rate": 1}, timeout=5)
    print(f"  F22(#{tgt['id']}) az={az:.1f} TAS: {r10.json()}")

# 11. 第一象限
print("\n[11] 第一象限目标")
st11, d11, t11, tas11 = s()
q1 = [t for t in st11["targets"] if 0 <= t.get("azimuth_deg", 0) < 90]
print(f"  第一象限: {[(t['id'], t['model']) for t in q1]}")
if q1:
    tgt = q1[0]
    az = tgt["azimuth_deg"]
    requests.post(f"{BASE}/api/mode", json={"mode": "stop"}, timeout=5)
    requests.post(f"{BASE}/api/steer", json={"azimuth": az}, timeout=5)
    r11 = requests.post(f"{BASE}/api/tasEngage", json={"target_id": tgt["id"], "data_rate": 1}, timeout=5)
    print(f"  #{tgt['id']} az={az:.1f} TAS: {r11.json()}")

# 12. TAS数据率查询
print("\n[12] TAS跟踪状态")
st12, d12, t12, tas12 = s()
print(f"  TAS: {st12.get('tas_tracking')}")

print("\n=== 完成 ===")
proc.terminate()
proc.wait(timeout=5)
