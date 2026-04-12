"""简单测试 agent_chat 是否能从 Ollama 获得响应"""
import requests, time

BASE = "http://localhost:8000"

# 先确认服务器活着
r = requests.get(f"{BASE}/api/state", timeout=5)
print(f"服务器: power={r.json()['power']}")

# 直接测试 agent_chat
t0 = time.time()
print("发送 agent_chat 请求...")
r = requests.post(f"{BASE}/api/agent/chat",
    json={"message": "你好", "session_id": "test"},
    timeout=125)
elapsed = time.time() - t0
print(f"响应时间: {elapsed:.1f}秒")
try:
    data = r.json()
    reply = data.get("reply", "")
    print(f"回复: {reply[:200]}")
except:
    print(f"错误: {r.text[:200]}")
