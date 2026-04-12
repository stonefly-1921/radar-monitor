"""测试服务器内部调 Ollama"""
import requests, sys

r = requests.get("http://localhost:8000/api/test/ollama", timeout=15)
data = r.json()
print("OK:", data.get("ok"))
print("elapsed:", data.get("elapsed"))
if data.get("error"):
    print("Error:", data.get("error"))
else:
    resp = data.get("response", {})
    content = resp.get("message", {}).get("content", "")
    print("Content length:", len(content))
    print("Content:", content[:50] if content else "EMPTY")
sys.exit(0)
