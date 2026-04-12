import requests, time, json

BASE = 'http://localhost:8000'

# Test 17 debug - 重点关注象限
print('=== Test17 Debug ===')
requests.post(BASE+'/api/simulation/reset', json={}, timeout=5)
requests.post(BASE+'/api/power', json={'state': 'on'}, timeout=5)
requests.post(BASE+'/api/mode', json={'mode': 'spin'}, timeout=5)
t0 = time.time()
try:
    r = requests.post(BASE+'/api/agent/chat', json={'message': '重点关注第一象限', 'session_id': 'quadrant'}, timeout=30)
    print('Status:', r.status_code)
    print('Content-Type:', r.headers.get('content-type', 'N/A'))
    print('Raw text:', r.text[:300])
    print('JSON:', json.dumps(r.json(), ensure_ascii=False, indent=2)[:300])
except Exception as e:
    print('Error:', e)
    print('Raw text:', r.text[:200] if 'r' in dir() else 'N/A')

print()
print('=== Test18 Debug ===')
requests.post(BASE+'/api/simulation/reset', json={}, timeout=5)
requests.post(BASE+'/api/power', json={'state': 'on'}, timeout=5)
requests.post(BASE+'/api/mode', json={'mode': 'spin'}, timeout=5)
t0 = time.time()
try:
    r = requests.post(BASE+'/api/agent/chat', json={'message': '在方位45度进行定方位监视', 'session_id': 'stepfail'}, timeout=60)
    print('Status:', r.status_code)
    print('Content-Type:', r.headers.get('content-type', 'N/A'))
    print('Raw text:', r.text[:500])
    try:
        j = r.json()
        print('JSON reply:', j.get('reply', '')[:200])
    except:
        print('Not JSON')
except Exception as e:
    print('Error:', e)
    if 'r' in dir():
        print('Raw text:', r.text[:300])
