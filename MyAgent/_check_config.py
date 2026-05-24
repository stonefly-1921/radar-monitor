# -*- coding: utf-8 -*-
import json, re, sys

path = 'C:/Users/15041/.openclaw/workspace/MyAgent/config/agent_config.json'
with open(path, encoding='utf-8') as f:
    content = f.read()

# Mask API keys
def mask_key(m):
    key = m.group(1)
    if len(key) > 8:
        return m.group(0).replace(key, key[:4] + '***' + key[-4:])
    return m.group(0)

masked = re.sub(r'"api_key"\s*:\s*"([^"]+)"', lambda m: '"api_key": "' + (m.group(1)[:4] + '***' if len(m.group(1)) > 8 else m.group(1)) + '"', content)
masked = re.sub(r'"MINIMAX_API_KEY"\s*:\s*"([^"]+)"', lambda m: '"MINIMAX_API_KEY": "' + (m.group(1)[:4] + '***' if len(m.group(1)) > 8 else m.group(1)) + '"', masked)

print(masked[:3000])
print('\n---MINIMAX key check---')
key_match = re.search(r'MINIMAX_API_KEY["\s:]+([^"\s]+)', masked)
if key_match:
    print('Found:', key_match.group(1)[:10])
else:
    print('No MINIMAX_API_KEY found in config')