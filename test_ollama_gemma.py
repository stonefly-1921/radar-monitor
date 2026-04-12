"""测试 gemma4 model instead"""
import urllib.request, json, time

# Try gemma4:e4b instead
t0 = time.time()
body = json.dumps({
    'model': 'gemma4:e4b',
    'prompt': 'Say OK',
    'stream': False,
    'options': {'num_predict': 10}
}).encode()
req = urllib.request.Request(
    'http://127.0.0.1:11434/api/generate',
    data=body,
    headers={'Content-Type': 'application/json'},
    method='POST'
)
try:
    resp = urllib.request.urlopen(req, timeout=20)
    data = json.loads(resp.read())
    print(f'gemma4 OK! 耗时: {time.time()-t0:.1f}s')
    print('response:', data.get('response', '')[:100])
except Exception as e:
    print(f'gemma4 失败: {e} 耗时: {time.time()-t0:.1f}s')

# Also check if qwen3 is stuck
body2 = json.dumps({
    'model': 'qwen3:4b-instruct',
    'prompt': 'Hi',
    'stream': False,
    'options': {'num_predict': 5}
}).encode()
req2 = urllib.request.Request(
    'http://127.0.0.1:11434/api/generate',
    data=body2,
    headers={'Content-Type': 'application/json'},
    method='POST'
)
t1 = time.time()
try:
    resp2 = urllib.request.urlopen(req2, timeout=15)
    data2 = json.loads(resp2.read())
    print(f'qwen3 OK! 耗时: {time.time()-t1:.1f}s')
    print('response:', data2.get('response', '')[:100])
except Exception as e:
    print(f'qwen3 失败: {e} 耗时: {time.time()-t1:.1f}s')
