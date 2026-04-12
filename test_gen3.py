import urllib.request, json, time

body = json.dumps({'model': 'gemma4:e4b', 'prompt': 'OK', 'stream': False}).encode()
headers = {
    'Content-Type': 'application/json',
}
req = urllib.request.Request(
    'http://127.0.0.1:11434/api/generate',
    data=body,
    headers=headers,
    method='POST'
)
t0 = time.time()
try:
    resp = urllib.request.urlopen(req, timeout=20)
    print('Status:', resp.status)
    print('Headers:', dict(resp.headers))
    data = json.loads(resp.read())
    print('OK: ' + str(time.time()-t0) + 's')
except urllib.error.HTTPError as e:
    print('HTTPError:', e.code, e.reason)
    print('Body:', e.read()[:200])
except Exception as e:
    print('Error:', type(e).__name__, str(e))
