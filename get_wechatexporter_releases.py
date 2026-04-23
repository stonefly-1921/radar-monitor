import urllib.request
import json
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

url = 'https://api.github.com/repos/BlueMatthew/WechatExporter/releases/latest'
try:
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, context=ctx, timeout=10) as r:
        data = json.loads(r.read())
        print('Tag:', data.get('tag_name'))
        print('Name:', data.get('name'))
        print('Body:', data.get('body', '')[:500])
        for asset in data.get('assets', []):
            print(f"  Asset: {asset['name']} - {asset['browser_download_url']}")
except Exception as e:
    print(f'Error: {e}')
