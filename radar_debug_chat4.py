import requests

BASE = 'http://localhost:8000'

tests = [
    '重点关注第一象限',
    '重点关注第二象限',
    '持续关注第一象限',
    '监控第一象限',
    '重点关注第一象限目标',
    '第一象限重点关注',
]

for msg in tests:
    requests.post(BASE+'/api/simulation/reset', json={}, timeout=5)
    requests.post(BASE+'/api/power', json={'state': 'on'}, timeout=5)
    r = requests.post(BASE+'/api/agent/chat', json={'message': msg, 'session_id': 'crash_test'}, timeout=30)
    print(str(r.status_code) + ' | ' + msg)
    if r.status_code != 200:
        print('  RAW: ' + r.text[:100])
