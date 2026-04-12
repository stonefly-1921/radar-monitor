"""测试 /api/test/llm 端点"""
import requests, sys, json

r = requests.get("http://localhost:8000/api/test/llm", timeout=130)
data = r.json()
print("OK:", data.get("ok"))
preview = data.get("result_preview", "")
# Try to decode as JSON
try:
    parsed = json.loads(preview)
    print("Parsed as JSON!")
    print("Content:", parsed)
except:
    print("Preview:", repr(preview[:300]))
sys.exit(0)
