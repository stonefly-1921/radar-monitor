"""探索 Ollama 0.20.3 的 API 端点"""
import urllib.request, json, time

endpoints = [
    '/api/chat',
    '/api/chat/completions', 
    '/api/v1/chat/completions',
    '/api/generate',
]

for ep in endpoints:
    t0 = time.time()
    body = json.dumps({
        'model': 'gemma4:e4b',
        'prompt': 'Say OK',
        'stream': False
    }).encode()
    req = urllib.request.Request(
        f'http://127.0.0.1:11434{ep}',
        data=body,
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        data = json.loads(resp.read())
        print(f'{ep}: OK ({time.time()-t0:.1f}s) - {str(data)[:100]}')
    except Exception as e:
        print(f'{ep}: FAILED - {e}')
