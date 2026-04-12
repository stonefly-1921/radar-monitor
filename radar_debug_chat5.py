import requests

BASE = 'http://localhost:8000'

# Test what MiniMax error looks like
requests.post(BASE+'/api/simulation/reset', json={}, timeout=5)
requests.post(BASE+'/api/power', json={'state': 'on'}, timeout=5)
requests.post(BASE+'/api/mode', json={'mode': 'spin'}, timeout=5)
r = requests.post(BASE+'/api/agent/chat', json={'message': '在方位45度进行定方位监视', 'session_id': 'perm_test'}, timeout=60)
print('Status:', r.status_code)
print('Content-Type:', r.headers.get('content-type', ''))
print('Raw:', r.text[:500])
try:
    j = r.json()
    print('JSON:', j)
except:
    print('Not JSON')
