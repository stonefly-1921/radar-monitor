import requests, json

BASE = 'http://localhost:8000'

# Simple test
print('Simple chat test:')
r = requests.post(BASE+'/api/agent/chat', json={'message': '你好', 'session_id': 'simpletest'}, timeout=30)
print('Status:', r.status_code)
print('Content-Type:', r.headers.get('content-type', 'N/A'))
print('Raw:', r.text[:200])
