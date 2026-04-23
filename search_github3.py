import urllib.request
import json
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# Search broadly for wechat export tools
queries = ['wechat chat export', '微信聊天记录导出', 'wechatmsg pc']
for q in queries:
    url = f'https://api.github.com/search/repositories?q={q.replace(" ", "+")}&per_page=5&sort=stars&order=desc'
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, context=ctx, timeout=10) as r:
            data = json.loads(r.read())
            print(f'\n=== {q} ===')
            for item in data.get('items', [])[:5]:
                print(f"  {item['name']} ({item['stargazers_count']} stars) - {item['html_url']}")
    except Exception as e:
        print(f'Error: {e}')
