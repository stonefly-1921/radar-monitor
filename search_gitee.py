import urllib.request
import json
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# Search Gitee for wechat exporter
url = 'https://gitee.com/api/v5/search/repositories?q=wechat+exporter&per_page=10&sort=stars&order=desc'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req, context=ctx, timeout=15) as r:
    data = json.loads(r.read())
    for item in data[:10]:
        print('Name:', item.get('name'))
        print('Stars:', item.get('stargazers_count'))
        print('URL:', item.get('html_url'))
        print('Desc:', item.get('description'))
        print()
