import requests, time, json

BASE = 'http://localhost:8000'

# Test 16: 快速连续 - 2次相同指令
print('=== Test16: 快速连续指令 ===')
requests.post(BASE+'/api/simulation/reset', json={}, timeout=5)
requests.post(BASE+'/api/power', json={'state': 'on'}, timeout=5)
t0 = time.time()
r1 = requests.post(BASE+'/api/agent/chat', json={'message': '全方位搜索', 'session_id': 'loop2a'}, timeout=30)
r2 = requests.post(BASE+'/api/agent/chat', json={'message': '全方位搜索', 'session_id': 'loop2a'}, timeout=30)
t2 = time.time() - t0
reply2 = r2.json().get('reply', '')
print('2次耗时: ' + str(round(t2,1)) + 's')
print('第2次状态: ' + str(r2.status_code))
print('第2次回复: ' + reply2[:100])
loop_caught = '循环' in reply2 or '重复' in reply2
print('Loop检测触发: ' + str(loop_caught) + ' (预期: False，3次才触发)')

# Test 17: preprocess象限
print()
print('=== Test17: 重点关注象限 ===')
requests.post(BASE+'/api/simulation/reset', json={}, timeout=5)
requests.post(BASE+'/api/power', json={'state': 'on'}, timeout=5)
requests.post(BASE+'/api/mode', json={'mode': 'spin'}, timeout=5)
t0 = time.time()
try:
    r = requests.post(BASE+'/api/agent/chat', json={'message': '重点关注第一象限', 'session_id': 'quadrant'}, timeout=30)
    reply = r.json().get('reply', '')
    print('耗时: ' + str(round(time.time()-t0,1)) + 's')
    print('回复: ' + reply[:150])
except Exception as e:
    print('错误: ' + str(e))

# Test 18: spin模式下set_steer
print()
print('=== Test18: spin模式定方位监视 ===')
requests.post(BASE+'/api/simulation/reset', json={}, timeout=5)
requests.post(BASE+'/api/power', json={'state': 'on'}, timeout=5)
requests.post(BASE+'/api/mode', json={'mode': 'spin'}, timeout=5)
t0 = time.time()
r = requests.post(BASE+'/api/agent/chat', json={'message': '在方位45度进行定方位监视', 'session_id': 'stepfail'}, timeout=60)
reply = r.json().get('reply', '')
print('耗时: ' + str(round(time.time()-t0,1)) + 's')
print('回复: ' + reply[:200])
spin_error = any(k in reply for k in ['转动', 'spin', '停转', '转动模式'])
print('包含转动模式错误提示: ' + str(spin_error))
