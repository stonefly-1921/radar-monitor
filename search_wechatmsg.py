import urllib.request
import json
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

url = 'https://api.github.com/search/repositories?q=wechatmsg&per_page=10&sort=stars&order=desc'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req, context=ctx, timeout=10) as r:
    data = json.loads(r.read())
    for item in data.get('items', [])[:10]:
        print('Name:', item['name'])
        print('Stars:', item['stargazers_count'])
        print('URL:', item['html_url'])
        print('Desc:', item.get('description', 'N/A'))
        print()
