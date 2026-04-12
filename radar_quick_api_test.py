"""
直接调 API + orchestrator.execute_plan，验证每步刷新状态是否正确。
不经过 LLM 调用。
"""
import requests, time, subprocess, sys, json

BASE = "http://localhost:8000"

def s():
    r = requests.get(f"{BASE}/api/state", timeout=5).json()
    det = len([t for t in r["targets"] if t.get("detected")])
    trk = len([t for t in r["targets"] if t.get("tracked")])
    return r, det, trk

# Kill + restart
subprocess.run(["powershell", "-Command",
    "Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | "
    "Select-Object -ExpandProperty OwningProcess | "
    "ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }"],
    capture_output=True)
time.sleep(2)
srv = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"],
    cwd=r"E:\radar-brain-github\backend",
    stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
time.sleep(5)
try:
    requests.get(f"{BASE}/api/state", timeout=3)
    print("服务器就绪")
except:
    print("服务器启动失败"); print(srv.stdout.read1(1000).decode(errors="replace")); sys.exit(1)

# Test: 模拟 orchestrator 调用 execute_plan 的流程
# 通过 /api/orchestrator/plan 或直接调 skill_executor
# 用 agent/chat 走 orchestrator 路径，但发一个简单的不触发预处理的指令

print("\n=== Test: 开机+全方位搜索 ===")
requests.post(f"{BASE}/api/simulation/reset", timeout=5)
r = requests.post(f"{BASE}/api/agent/chat",
    json={"message": "全方位搜索", "session_id": "qtest"},
    timeout=60)
try:
    data = r.json()
    print(f"回复: {str(data.get('reply',''))[:200]}")
except:
    print(f"错误: {r.text[:200]}")

print("\n=== Test: 停转后对1号目标跟踪 ===")
# 等目标起批
time.sleep(15)
st, d, t = s()
print(f"检测={d} 起批={t}")
if d == 0 and t == 0:
    print("警告：15秒后仍无目标，可能是搜索扇区问题")

print("\n完成")
srv.terminate(); srv.wait(timeout=5)
