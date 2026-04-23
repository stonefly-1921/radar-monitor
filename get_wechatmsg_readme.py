import urllib.request
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# Get README
url = 'https://raw.githubusercontent.com/LC044/WeChatMsg/master/readme.md'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
try:
    with urllib.request.urlopen(req, context=ctx, timeout=10) as r:
        readme = r.read().decode('utf-8', errors='replace')
        print(readme[:3000])
except Exception as e:
    print('Error:', e)
