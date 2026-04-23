import urllib.request
import json
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# Get tags
url = 'https://api.github.com/repos/LC044/WeChatMsg/tags'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req, context=ctx, timeout=10) as r:
    data = json.loads(r.read())
    print('Tags:', [d['name'] for d in data[:5]])

# Get the repo readme
url2 = 'https://raw.githubusercontent.com/LC044/WeChatMsg/main/README.md'
try:
    req2 = urllib.request.Request(url2, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req2, context=ctx, timeout=10) as r:
        readme = r.read().decode('utf-8', errors='replace')[:2000]
        print('\nREADME:\n', readme)
except Exception as e:
    print('README error:', e)
