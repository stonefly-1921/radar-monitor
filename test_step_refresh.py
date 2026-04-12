"""
直接用Python标准库测试 step_executor 的状态刷新修复。
通过 urllib 直接调 API。
"""
import urllib.request
import urllib.error
import json
import time
import subprocess
import sys

BASE = "http://localhost:8000"

def api_get(path):
    try:
        r = urllib.request.urlopen(f"{BASE}{path}", timeout=5)
        return json.loads(r.read().decode())
    except Exception as e:
        return {"error": str(e)}

def api_post(path, data):
    try:
        body = json.dumps(data).encode()
        req = urllib.request.Request(f"{BASE}{path}", data=body,
                                     headers={"Content-Type": "application/json"})
        r = urllib.request.urlopen(req, timeout=5)
        return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return json.loads(e.read().decode()) if e.fp else {"error": str(e)}
    except Exception as e:
        return {"error": str(e)}

def s():
    st = api_get("/api/state")
    det = len([t for t in st.get("targets", []) if t.get("detected")])
    trk = len([t for t in st.get("targets", []) if t.get("tracked")])
    return st, det, trk

# ---- Kill and restart server ----
print("停止旧服务器...")
subprocess.run(["powershell", "-Command",
    "Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | "
    "Select-Object -ExpandProperty OwningProcess | "
    "ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }"],
    capture_output=True)
time.sleep(3)

print("启动新服务器...")
srv = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"],
    cwd=r"E:\radar-brain-github\backend",
    stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
time.sleep(6)

st = api_get("/api/state")
if "error" in st:
    print(f"服务器启动失败: {st}")
    srv.terminate()
    sys.exit(1)
print(f"服务器就绪: power={st['power']}")

# ---- Test: orchestrator 通过 agent/chat 走一条简单指令 ----
# 发一个不会触发预处理的指令（不是"开机+识别"组合）
requests.post(f"{BASE}/api/simulation/reset", timeout=5)
print("\n=== 测试：开机并全方位搜索 ===")
data = api_post("/api/agent/chat", {"message": "开机并全方位搜索", "session_id": "steptest"})
print(f"结果: {str(data)[:300]}")

# 检查服务器是否还在响应
st2 = api_get("/api/state")
print(f"\n服务器状态: power={st2['power']} mode={st2['mode']}")

print("\n等待15秒让目标进入检测...")
time.sleep(15)
st3, d3, t3 = s()
print(f"15秒后: 检测={d3} 起批={t3}")
for t in st3["targets"]:
    if t.get("detected"):
        print(f"  #{t['id']} {t['model']} az={t['azimuth_deg']:.1f} dist={t['distance_m']/1000:.0f}km")

print("\n=== 测试：对1号目标跟踪 ===")
data2 = api_post("/api/agent/chat", {"message": "对1号目标进行跟踪", "session_id": "steptest2"})
print(f"结果: {str(data2)[:300]}")
st4, d4, t4 = s()
print(f"TAS: {st4.get('tas_tracking')}")

print("\n完成")
srv.terminate()
srv.wait(timeout=5)
