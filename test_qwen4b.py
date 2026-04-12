import urllib.request, json, time

t0 = time.time()
body = json.dumps({'model': 'qwen3:4b-instruct', 'prompt': '你好，返回OK', 'stream': False}).encode()
req = urllib.request.Request(
    'http://127.0.0.1:11434/api/generate',
    data=body,
    headers={'Content-Type': 'application/json'},
    method='POST'
)
resp = urllib.request.urlopen(req, timeout=30)
data = json.loads(resp.read())
print(f'耗时: {time.time()-t0:.1f}s')
print('response:', data.get('response', '')[:200])
print('done:', data.get('done'))
