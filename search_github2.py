import urllib.request
import json
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# Search for WechatTool
url = 'https://api.github.com/search/repositories?q=WechatTool+wechat+export&per_page=10'
try:
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, context=ctx, timeout=10) as r:
        data = json.loads(r.read())
        for item in data.get('items', [])[:10]:
            print(f"Name: {item['name']}, Stars: {item['stargazers_count']}, URL: {item['html_url']}")
            print(f"  Desc: {item.get('description', 'N/A')}")
except Exception as e:
    print(f'Error: {e}')
