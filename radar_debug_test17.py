"""精准调试 Test17 500错误"""
import requests
import logging
import traceback
import sys

BASE = 'http://localhost:8000'

# 设置 console 输出 UTF-8
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Test 17 precise
print('=== Test17 Debug: 重点关注第一象限 ===')
requests.post(BASE+'/api/simulation/reset', json={}, timeout=5)
requests.post(BASE+'/api/power', json={'state': 'on'}, timeout=5)

import time
t0 = time.time()
try:
    r = requests.post(
        BASE+'/api/agent/chat',
        json={'message': '重点关注第一象限', 'session_id': 'debug17'},
        timeout=60
    )
    elapsed = time.time() - t0
    print('Status:', r.status_code)
    print('Elapsed:', elapsed)
    print('Content-Type:', r.headers.get('content-type', ''))
    print('Raw text:', r.text[:300])
    if r.status_code == 200:
        try:
            j = r.json()
            print('Reply:', j.get('reply', '')[:200])
        except:
            print('Not JSON')
    else:
        # Try to get traceback from server
        print('Error response:', r.text)
except Exception as e:
    elapsed = time.time() - t0
    print('Request failed after', elapsed, 's:', e)
    print('Traceback:', traceback.format_exc())

# Also test a simpler quadrant message
print()
print('=== Simpler test: 重点关注 ===')
requests.post(BASE+'/api/simulation/reset', json={}, timeout=5)
requests.post(BASE+'/api/power', json={'state': 'on'}, timeout=5)
t0 = time.time()
r = requests.post(
    BASE+'/api/agent/chat',
    json={'message': '重点关注', 'session_id': 'debug_simple'},
    timeout=60
)
print('Status:', r.status_code, 'Elapsed:', round(time.time()-t0, 1), 's')
if r.status_code == 200:
    try:
        print('Reply:', r.json().get('reply', '')[:100])
    except:
        print('Raw:', r.text[:100])
else:
    print('Raw:', r.text[:200])
