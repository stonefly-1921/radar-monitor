"""测试 ollama qwen3:4b-instruct 简单调用"""
import urllib.request, json, time

t0 = time.time()
body = json.dumps({
    'model': 'qwen3:4b-instruct',
    'prompt': 'OK',
    'stream': False,
    'options': {'num_predict': 5}
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
    print(f'成功! 耗时: {time.time()-t0:.1f}s')
    print('response:', data.get('response', '')[:100])
except Exception as e:
    print(f'失败: {e} 耗时: {time.time()-t0:.1f}s')
