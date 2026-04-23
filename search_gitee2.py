import urllib.request
import json
import ssl
import urllib.parse

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# Search Gitee for wechat exporter
q = urllib.parse.quote('微信聊天记录导出')
url = f'https://gitee.com/api/v5/search/repositories?q={q}&per_page=10&sort=stars&order=desc'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req, context=ctx, timeout=15) as r:
    data = json.loads(r.read())
    for item in data[:10]:
        print('Name:', item.get('name'))
        print('Stars:', item.get('stargazers_count'))
        print('URL:', item.get('html_url'))
        print('Desc:', item.get('description'))
        print()
