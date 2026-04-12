"""测试 Ollama chat API 响应"""
import requests, sys

r = requests.post("http://127.0.0.1:11434/api/chat",
    json={"model": "qwen3:4b-instruct", "messages": [{"role": "user", "content": "say hi"}], "stream": False},
    timeout=15)
data = r.json()
content = data.get("message", {}).get("content", "")
print(f"OK time: {r.elapsed.total_seconds():.1f}s content length: {len(content)}")
if content:
    print("Content preview:", content[:100].encode('utf-8'))
sys.exit(0)
