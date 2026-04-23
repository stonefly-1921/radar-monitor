import urllib.request
import json
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# Search for WeChatMsg download
url = 'https://api.github.com/search/code?q=WeChatMsg+exe+in:path&per_page=5'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0', 'Accept': 'application/vnd.github.v3+json'})
try:
    with urllib.request.urlopen(req, context=ctx, timeout=10) as r:
        data = json.loads(r.read())
        print('Code results:', data.get('total_count'))
        for item in data.get('items', [])[:5]:
            print(' ', item['path'])
except Exception as e:
    print('Error:', e)

# Also check the repo content
url2 = 'https://api.github.com/repos/LC044/WeChatMsg/contents'
req2 = urllib.request.Request(url2, headers={'User-Agent': 'Mozilla/5.0'})
try:
    with urllib.request.urlopen(req2, context=ctx, timeout=10) as r:
        data = json.loads(r.read())
        for item in data[:10]:
            print('Content:', item['name'], '| type:', item['type'])
except Exception as e:
    print('Content error:', e)
