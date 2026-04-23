import urllib.request
import ssl
import os

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# Try common Gitee mirrors for WechatExporter
urls_to_try = [
    'https://gitee.com/wechat-exporter/WechatExporter',
    'https://gitee.com/mso/WechatExporter',
    'https://gitee.com/wmhome/WechatExporter',
    'https://gitee.com/blue/WechatExporter',
]

headers = {'User-Agent': 'Mozilla/5.0'}

for url in urls_to_try:
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=10) as r:
            print(f'OK: {url}')
            content = r.read(200).decode('utf-8', errors='replace')
            print(f'  Content: {content[:100]}')
    except Exception as e:
        print(f'FAIL: {url} - {str(e)[:50]}')
