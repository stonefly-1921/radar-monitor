"""测试 orchestrator.receive()"""
import requests, sys

print("测试 /api/test/orchestrator...")
r = requests.post("http://localhost:8000/api/test/orchestrator",
    json={"message": "开机并全方位搜索"},
    timeout=130)
data = r.json()
print("OK:", data.get("ok"))
print("Error:", data.get("error"))
print("Traceback:", (data.get("traceback") or "")[:300])
print("Reply:", data.get("reply", "")[:200])
print("Plan:", data.get("plan_summary", "")[:200])
sys.exit(0)
