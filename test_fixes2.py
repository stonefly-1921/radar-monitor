"""完整修复验证 - 每次测试用唯一session"""
import requests, time

BASE = "http://localhost:8000"

def reset():
    requests.post(f"{BASE}/api/simulation/reset", json={}, timeout=5)
    requests.post(f"{BASE}/api/power", json={"state": "off"}, timeout=5)

def chat(message, session=None, timeout=120):
    if session is None:
        session = f"t{int(time.time()*1000)}"
    t0 = time.time()
    try:
        r = requests.post(f"{BASE}/api/agent/chat",
            json={"message": message, "session_id": session},
            timeout=timeout)
        return time.time()-t0, r.status_code, r.json().get("reply","")[:400]
    except Exception as e:
        return time.time()-t0, "error", str(e)

# === Fix 2: 雷达未开机 + TAS指令 → 应该自动开机 ===
print("=== Fix 2: 雷达未开机时 tasEngage 自动开机 ===")
reset()
r = requests.get(f"{BASE}/api/state", timeout=5)
print(f"  雷达当前: power={r.json()['power']}")
_, code, reply = chat("TAS跟踪1号目标", timeout=120)
print(f"  耗时:{_:.0f}s 状态:{code}")
print(f"  回复: {reply}")
print()

# === 直接测试 tas_engage Step（不走LLM编排，走agent_loop预处理）===
print("=== Fix 1: TAS不需要识别直接接入 ===")
reset()
# 开机并制造一个目标
requests.post(f"{BASE}/api/power", json={"state": "on"}, timeout=5)
r = requests.post(f"{BASE}/api/mode", json={"mode": "spin"}, timeout=5)
# 等待目标出现
time.sleep(5)
r = requests.get(f"{BASE}/api/state", timeout=5)
print(f"  雷达: power={r.json()['power']} mode={r.json()['mode']}")
tracks = requests.get(f"{BASE}/api/tracks", timeout=5).json()
print(f"  目标: {tracks.get('total',0)} 批")
if tracks.get('total', 0) > 0:
    tgt = tracks['tracks'][0]
    print(f"  目标1: id={tgt['id']} tracked={tgt.get('tracked')} az={tgt.get('azimuth_deg')}")
