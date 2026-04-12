import urllib.request, json, time

body = json.dumps({'model': 'gemma4:e4b', 'prompt': 'Say OK', 'stream': False}).encode()
req = urllib.request.Request(
    'http://127.0.0.1:11434/api/generate',
    data=body,
    headers={'Content-Type': 'application/json'},
    method='POST'
)
t0 = time.time()
try:
    resp = urllib.request.urlopen(req, timeout=20)
    data = json.loads(resp.read())
    print('OK: ' + str(time.time()-t0) + 's, response: ' + str(data.get('response', ''))[:50])
except Exception as e:
    print('Error: ' + str(e))
