import urllib.request, json, time

# Test /api/generate with explicit headers
body = json.dumps({'model': 'gemma4:e4b', 'prompt': 'OK', 'stream': False}).encode()
headers = {
    'Content-Type': 'application/json',
    'User-Agent': 'Ollama/0.20.3'
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
    data = json.loads(resp.read())
    print('OK: ' + str(time.time()-t0) + 's, response: ' + str(data.get('response',''))[:100])
except Exception as e:
    print('Error: ' + str(e))
