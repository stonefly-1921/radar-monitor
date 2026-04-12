import requests
import time
import json

BASE = "http://localhost:8000"

def s():
    return requests.get(f"{BASE}/api/state", timeout=5).json()

def chat(msg):
    print(f"  [发送] {msg}")
    r = requests.post(f"{BASE}/api/agent/chat", json={"message": msg, "session_id": "steptest"}, timeout=60)
    try:
        data = r.json()
        reply = data.get("reply", data.get("response", str(data)))
        print(f"  [回复] {reply[:300]}")
        return reply
    except:
        print(f"  [错误] {r.text[:200]}")
        return None

# Reset
print("Reset...")
requests.post(f"{BASE}/api/simulation/reset", timeout=5)

# Test 1: 开机器
print("\n[1] 开机+全方位搜索")
chat("开机并全方位搜索")
time.sleep(3)
st = s()
print(f"  状态: power={st['power']}, mode={st['mode']}, targets={len([t for t in st['targets'] if t.get('detected')])}det / {len([t for t in st['targets'] if t.get('tracked')])}track")

# Wait for targets
print("  等待10秒让目标进入检测...")
time.sleep(10)
st2 = s()
print(f"  10秒后: {len([t for t in st2['targets'] if t.get('detected')])}det / {len([t for t in st2['targets'] if t.get('tracked')])}track")
for t in st2['targets']:
    if t.get('detected'):
        print(f"    #{t['id']} {t['model']} az={t['azimuth_deg']:.0f} dist={t['distance_m']/1000:.0f}km tracked={t.get('tracked')}")

print("\n[2] 查目标数")
chat("目前起批几个目标?")

print("\n[3] TAS在转动模式")
chat("对1号目标进行跟踪")

print("\n[4] 停转后TAS")
chat("先停转，然后对1号目标进行跟踪")
st4 = s()
print(f"  TAS: {st4.get('tas_tracking')}, steer={st4.get('steer_azimuth_deg',0):.1f}度")

print("\n[5] 数据率10Hz")
chat("把1号目标跟踪数据率改成10赫兹")
st5 = s()
print(f"  TAS: {st5.get('tas_tracking')}")

print("\n[6] 识别")
chat("对1号目标进行识别")
time.sleep(2)
st6 = s()
t1 = next((t for t in st6['targets'] if t['id']==1), None)
print(f"  识别结果: {t1.get('identified_model') if t1 else 'N/A'}")

print("\n[7] 已识别类型")
chat("当前有哪些类型的已识别目标?")

print("\n全部完成")
