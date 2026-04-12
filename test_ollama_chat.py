"""测试 Ollama /api/chat 端点"""
import urllib.request, json, time

t0 = time.time()
body = json.dumps({
    'model': 'gemma4:e4b',
    'messages': [{'role': 'user', 'content': 'Say OK'}],
    'stream': False
}).encode()
req = urllib.request.Request(
    'http://127.0.0.1:11434/api/chat',
    data=body,
    headers={'Content-Type': 'application/json'},
    method='POST'
)
try:
    resp = urllib.request.urlopen(req, timeout=20)
    data = json.loads(resp.read())
    print(f'成功! 耗时: {time.time()-t0:.1f}s')
    print('response:', json.dumps(data, indent=2)[:500])
except Exception as e:
    print(f'失败: {e} 耗时: {time.time()-t0:.1f}s')
