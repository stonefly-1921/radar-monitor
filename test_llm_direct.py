"""测试通过 agent_loop LLM client 调 Ollama"""
import requests, sys

print("测试 /api/test/llm（直接调 _do）...")
r = requests.get("http://localhost:8000/api/test/llm", timeout=130)
data = r.json()
print("OK:", data.get("ok"))
if data.get("error"):
    print("Error:", data.get("error"))
if data.get("traceback"):
    print("Traceback:", data.get("traceback"))
print("Preview:", data.get("result_preview", "")[:200])
sys.exit(0)
