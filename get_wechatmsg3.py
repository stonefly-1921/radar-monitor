import urllib.request
import json
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# Try releases with per_page
url = 'https://api.github.com/repos/LC044/WeChatMsg/releases?per_page=5'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req, context=ctx, timeout=10) as r:
    data = json.loads(r.read())
    if data:
        for d in data[:3]:
            print('Tag:', d.get('tag_name'), '| Name:', d.get('name'))
            for asset in d.get('assets', []):
                print('  Asset:', asset['name'], '|', asset['browser_download_url'])
            print('Body preview:', d.get('body', '')[:300])
            print()
    else:
        print('No releases found')
    
# Check if there's a wiki
url2 = 'https://api.github.com/repos/LC044/WeChatMsg/wiki'
req2 = urllib.request.Request(url2, headers={'User-Agent': 'Mozilla/5.0'})
try:
    with urllib.request.urlopen(req2, context=ctx, timeout=10) as r:
        print('Wiki available')
except Exception as e:
    print('Wiki error:', e)
