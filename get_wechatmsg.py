import urllib.request
import json
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

url = 'https://api.github.com/repos/LC044/WeChatMsg'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req, context=ctx, timeout=10) as r:
    data = json.loads(r.read())
    print('Stars:', data.get('stargazers_count'))
    print('Description:', data.get('description'))
    print('Readme (first 1000):')
    print(data.get('body', 'N/A')[:1000])

# Get releases
url2 = 'https://api.github.com/repos/LC044/WeChatMsg/releases/latest'
try:
    req2 = urllib.request.Request(url2, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req2, context=ctx, timeout=10) as r:
        d = json.loads(r.read())
        print('\nLatest release:', d.get('tag_name'))
        print('Name:', d.get('name'))
        for asset in d.get('assets', []):
            print('  Asset:', asset['name'], '|', asset['browser_download_url'])
except Exception as e:
    print('Release error:', e)
