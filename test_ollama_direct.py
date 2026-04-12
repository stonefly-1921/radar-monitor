"""直接测试 Ollama /api/chat 响应速度"""
import urllib.request, json, time

url = "http://127.0.0.1:11434/api/chat"
body = {
    "model": "qwen3:4b-instruct",
    "messages": [{"role": "user", "content": "hi"}],
    "stream": False
}

t0 = time.time()
try:
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    r = urllib.request.urlopen(req, timeout=30)
    elapsed = time.time() - t0
    print(f"Ollama响应时间: {elapsed:.1f}秒")
    print(f"内容: {r.read().decode()[:200]}")
except Exception as e:
    elapsed = time.time() - t0
    print(f"失败({elapsed:.1f}秒): {e}")
