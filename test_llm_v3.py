"""测试 /api/test/llm 端点"""
import requests, sys

r = requests.get("http://localhost:8000/api/test/llm", timeout=130)
data = r.json()
print("OK:", data.get("ok"))
print("Error:", data.get("error"))
print("Traceback:", data.get("traceback"))
preview = data.get("result_preview", "")
# Just print as repr to avoid GBK issues
print("Preview repr:", repr(preview[:200]))
sys.exit(0)
