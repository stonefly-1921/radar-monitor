"""Test18 simple"""
import requests, json

BASE = "http://localhost:8000"

# Setup: spin mode
requests.post(BASE+"/api/simulation/reset", json={}, timeout=5)
requests.post(BASE+"/api/power", json={"state": "on"}, timeout=5)
requests.post(BASE+"/api/mode", json={"mode": "spin"}, timeout=5)

# Chat
r = requests.post(BASE+"/api/agent/chat",
    json={"message": "在方位45度进行定方位监视", "session_id": "test18simple"},
    timeout=30)
print("Status:", r.status_code)
if r.status_code == 200:
    reply = r.json().get("reply", "")
    with open(r"C:\Users\15041\.openclaw\workspace\test18simple_reply.txt", "w", encoding="utf-8") as f:
        f.write(reply)
    print("Length:", len(reply))
    print("Reply:", reply[:200])
