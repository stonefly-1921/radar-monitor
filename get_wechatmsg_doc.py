import urllib.request
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# Get doc contents
url = 'https://api.github.com/repos/LC044/WeChatMsg/contents/doc'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req, context=ctx, timeout=10) as r:
    import json
    data = json.loads(r.read())
    for item in data:
        print(item['name'], '| type:', item['type'], '| url:', item.get('download_url', ''))
