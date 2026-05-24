# -*- coding: utf-8 -*-
import json, urllib.request, os

key = open('C:/Users/15041/.openclaw/workspace/MyAgent/_apikey.txt').read().strip()
url = 'https://api.minimax.chat/v1/text/chatcompletion_v2'

models = ['MiniMax-Text-01', 'MiniMax-Text', 'abab5-chat', 'abab6-chat', 'minimax-chat', 'chatanywhere']

for model in models:
    payload = {'model': model, 'messages': [{'role': 'user', 'content': 'hi'}], 'max_tokens': 10}
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'}, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode('utf-8'))
            status = result.get('base_resp', {}).get('status_code', 0)
            msg = result.get('base_resp', {}).get('status_msg', '')
            choices = result.get('choices')
            if status == 0 and choices:
                content = choices[0].get('message', {}).get('content', '')
                print('SUCCESS: ' + model + ' -> ' + content)
            else:
                print('FAIL ' + str(status) + ': ' + model + ' -> ' + msg)
    except Exception as e:
        print('ERROR: ' + model + ' -> ' + str(e))