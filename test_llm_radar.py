"""测试完整的 orchestrator + step 流程"""
import requests, time, subprocess, sys, json

BASE = "http://localhost:8000"

def api_get(path):
    return requests.get(f"{BASE}{path}", timeout=5).json()

def api_post(path, data):
    return requests.post(f"{BASE}{path}", json=data, timeout=130).json()

# 确保服务器在跑
try:
    st = api_get("/api/state")
    print(f"服务器就绪: power={st['power']}")
except Exception as e:
    print(f"服务器未启动: {e}"); sys.exit(1)

# 重置+开机
requests.post(f"{BASE}/api/simulation/reset", timeout=5)
requests.post(f"{BASE}/api/power", json={"state": "on"}, timeout=5)
requests.post(f"{BASE}/api/search_zone", json={
    "azimuth_lo": -180, "azimuth_hi": 180,
    "elevation_lo": -5, "elevation_hi": 70,
    "range_min": 5000, "range_max": 450000
}, timeout=5)
requests.post(f"{BASE}/api/mode", json={"mode": "spin"}, timeout=5)
print("雷达已开机")

# 等目标
print("等待目标出现...")
for i in range(6):
    time.sleep(2)
    st = api_get("/api/state")
    det = len([t for t in st["targets"] if t.get("detected")])
    if det > 0:
        print(f"  [{2*(i+1)}秒] 检测到{det}批目标")
        break
    print(f"  [{2*(i+1)}秒] 检测=0", end="\r")

# 测试 orchestrator 路径
print("\n\n=== 测试 orchestrator 路径 ===")

tests = [
    ("开机并全方位搜索", "应该执行 power_on → set_mode spin"),
    ("目前起批几个目标？", "应该返回目标数量"),
    ("对1号目标进行跟踪", "应该执行 tas_engage（需先停转）"),
    ("把1号目标跟踪数据率改成10赫兹", "应该执行 set_tas_data_rate"),
    ("对1号目标进行识别", "应该执行 identify"),
    ("当前有哪些类型的已识别目标？", "应该返回已识别目标列表"),
]

for msg, desc in tests:
    print(f"\n>>> {msg}（{desc}）")
    r = api_post("/api/agent/chat", {"message": msg, "session_id": "test"})
    reply = r.get("reply", "")
    print(f"回复: {reply[:150]}")
    time.sleep(1)

print("\n完成")
