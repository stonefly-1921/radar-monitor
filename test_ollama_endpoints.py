"""测试 Ollama /api/chat/completions 端点"""
import urllib.request, json, time

# Test /api/chat/completions
t0 = time.time()
body = json.dumps({
    'model': 'gemma4:e4b',
    'messages': [{'role': 'user', 'content': 'Say OK'}],
    'stream': False
}).encode()
req = urllib.request.Request(
    'http://127.0.0.1:11434/api/chat/completions',
    data=body,
    headers={'Content-Type': 'application/json'},
    method='POST'
)
try:
    resp = urllib.request.urlopen(req, timeout=20)
    data = json.loads(resp.read())
    print(f'/api/chat/completions 成功! 耗时: {time.time()-t0:.1f}s')
    print('response:', json.dumps(data, indent=2)[:500])
except Exception as e:
    print(f'/api/chat/completions 失败: {e}')
