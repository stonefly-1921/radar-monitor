import requests, json

BASE = 'http://localhost:8000'

tests = [
    ('重点关注第一象限', 'quadrant_fresh'),
    ('重点关注', 'guanzhu_fresh'),
    ('第一象限', 'quadrant1_fresh'),
    ('在方位45度进行定方位监视', 'fangwei_fresh'),
    ('方位45度定方位', 'fangwei2_fresh'),
    ('定方位', 'dingfangwei_fresh'),
]

for msg, session in tests:
    # Reset state first
    requests.post(BASE+'/api/simulation/reset', json={}, timeout=5)
    requests.post(BASE+'/api/power', json={'state': 'on'}, timeout=5)
    requests.post(BASE+'/api/mode', json={'mode': 'spin'}, timeout=5)
    
    r = requests.post(BASE+'/api/agent/chat', json={'message': msg, 'session_id': session}, timeout=60)
    print('msg=' + msg[:15] + '... session=' + session + ' -> status=' + str(r.status_code))
    if r.status_code != 200:
        print('  RAW: ' + r.text[:100])
    else:
        reply = r.json().get('reply', '')[:80]
        print('  reply: ' + reply)
    print()
