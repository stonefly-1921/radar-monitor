import requests
import time
import subprocess
import sys

BASE = "http://localhost:8000"

def s():
    r = requests.get(f"{BASE}/api/state", timeout=5).json()
    detected = len([t for t in r["targets"] if t.get("detected")])
    tracked = len([t for t in r["targets"] if t.get("tracked")])
    tas = len(r.get("tas_tracking", {}))
    return r, detected, tracked, tas

# Kill and restart server
subprocess.run(["powershell", "-Command", 
    "Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }"],
    capture_output=True)
time.sleep(2)
proc = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"],
    cwd=r"E:\radar-brain-github\backend",
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
)
time.sleep(5)
try:
    requests.get(f"{BASE}/api/state", timeout=5)
    print("服务器就绪")
except:
    print("服务器启动失败")
    print(proc.stdout.read1(2000).decode(errors="replace"))
    sys.exit(1)

def chat(msg):
    print(f"\n>>> {msg}")
    r = requests.post(f"{BASE}/api/agent/chat", json={"message": msg, "session_id": "test2"}, timeout=120)
    try:
        data = r.json()
        reply = data.get("reply", data.get("response", str(data)))
        print(f"回复: {reply[:400]}")
        return reply
    except:
        print(f"错误: {r.text[:200]}")
        return None

def wait_for_targets(min_detected=1, timeout=20):
    """等待至少min_detected个目标被检测到"""
    for i in range(timeout // 2):
        time.sleep(2)
        st, d, t, _ = s()
        if d >= min_detected:
            print(f"  [{2*(i+1)}秒] 检测到{d}批，起批{t}批")
            return st, d, t
        print(f"  [{2*(i+1)}秒] 检测={d} 起批={t}", end="\r")
    return s()

# ===== 基础功能 =====
requests.post(f"{BASE}/api/simulation/reset", timeout=5)
requests.post(f"{BASE}/api/power", json={"state": "on"}, timeout=5)
requests.post(f"{BASE}/api/search_zone", json={
    "azimuth_lo": -180, "azimuth_hi": 180,
    "elevation_lo": -5, "elevation_hi": 70,
    "range_min": 5000, "range_max": 450000
}, timeout=5)
requests.post(f"{BASE}/api/mode", json={"mode": "spin"}, timeout=5)

print("=" * 60)
print("组别一：基础功能")
print("=" * 60)

print("\n[1] 开机并全方位搜索")
chat("开机并全方位搜索")
time.sleep(2)
st1, d1, t1, _ = s()
print(f"  状态: 检测={d1} 起批={t1}")

print("\n[2] 反馈当前目标数")
chat("目前起批几个目标？")
st2, d2, t2, _ = wait_for_targets(1)
print(f"  最终: 检测={d2} 起批={t2}")

print("\n[3] TAS在转动模式")
chat("对1号目标进行跟踪")

print("\n[4] 停转后TAS")
chat("先停转，然后对1号目标进行跟踪")
st4, d4, t4, tas4 = s()
print(f"  TAS: {st4.get('tas_tracking')}")
print(f"  steer: {st4.get('steer_azimuth_deg',0):.1f}度")

print("\n[5] 数据率10Hz")
chat("把1号目标跟踪数据率改成10赫兹")
st5, d5, t5, tas5 = s()
print(f"  TAS: {st5.get('tas_tracking')}")

print("\n[6] 识别")
chat("对1号目标进行识别")
time.sleep(2)
st6, d6, t6, tas6 = s()
t1v = next((t for t in st6["targets"] if t["id"]==1), None)
print(f"  identified: {t1v.get('identified_model') if t1v else 'N/A'}")

print("\n[7] 已识别类型")
chat("当前有哪些类型的已识别目标？")

print("\n" + "=" * 60)
print("组别二：高级功能")
print("=" * 60)

requests.post(f"{BASE}/api/simulation/reset", timeout=5)
requests.post(f"{BASE}/api/power", json={"state": "on"}, timeout=5)
requests.post(f"{BASE}/api/search_zone", json={
    "azimuth_lo": -180, "azimuth_hi": 180,
    "elevation_lo": -5, "elevation_hi": 70,
    "range_min": 5000, "range_max": 450000
}, timeout=5)
requests.post(f"{BASE}/api/mode", json={"mode": "spin"}, timeout=5)
print("重置+开机，等待目标...")
st_b, d_b, t_b = wait_for_targets(3)
print(f"  就绪: 检测={d_b} 起批={t_b}")

print("\n[8] 对所有目标识别（转动→应先停转）")
chat("请对所有目标进行识别，并上报识别结果")

print("\n[9] 多目标TAS")
chat("请对1号、2号、3号目标转TAS跟踪")
st9, d9, t9, tas9 = s()
print(f"  TAS: {st9.get('tas_tracking')}")

print("\n[10] F22 TAS")
chat("请对F22这样的目标进行TAS跟踪")
st10, d10, t10, tas10 = s()
print(f"  TAS: {st10.get('tas_tracking')}")

print("\n[11] 第一象限目标")
chat("请对第一象限的目标转跟踪")
st11, d11, t11, tas11 = s()
print(f"  TAS: {st11.get('tas_tracking')}")

print("\n[12] 跟踪了哪些+数据率")
chat("当前跟踪了哪些目标？每个目标的数据率是多少？")

print("\n" + "=" * 60)
print("全部完成")
print("=" * 60)
proc.terminate()
proc.wait(timeout=5)
