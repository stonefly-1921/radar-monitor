import urllib.request
import json
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

url = 'https://api.github.com/repos/BlueMatthew/WechatExporter'
try:
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, context=ctx, timeout=10) as r:
        data = json.loads(r.read())
        print('Stars:', data.get('stargazers_count'))
        print('Description:', data.get('description'))
        print('Latest release:', data.get('tag_name'))
        print('URL:', data.get('html_url'))
        releases_url = data.get('releases_url', '').replace('{/id}', '')
        print('Releases URL:', releases_url)
except Exception as e:
    print(f'Error: {e}')
