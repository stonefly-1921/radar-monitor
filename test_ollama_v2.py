"""测试 Ollama chat API"""
import requests, time

t0 = time.time()
try:
    r = requests.post("http://127.0.0.1:11434/api/chat",
        json={"model": "qwen3:4b-instruct", "messages": [{"role": "user", "content": "hi"}], "stream": False},
        timeout=30)
    elapsed = time.time() - t0
    print(f"响应时间: {elapsed:.1f}秒")
    print(f"状态: {r.status_code}")
    print(f"内容: {r.text[:300]}")
except Exception as e:
    elapsed = time.time() - t0
    print(f"失败({elapsed:.1f}秒): {e}")
