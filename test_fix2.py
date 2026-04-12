import requests, time
t0 = time.time()
r = requests.post('http://localhost:8000/api/agent/chat',
    json={'message': '对1号目标接入TAS', 'session_id': 'fix2'},
    timeout=120)
print(f'Done in {time.time()-t0:.1f}s: {r.status_code} - {r.json().get("reply", "")[:200]}')
