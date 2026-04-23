import os

base = r'C:\Users\15041\xwechat_files\backup\wshjustin\8b28002d18b0751decef2edc17ff6c20\files\1'
entries = os.listdir(base)
print('Total entries in files1:', len(entries))

sizes = []
for e in entries:
    p = os.path.join(base, e)
    sz = os.path.getsize(p)
    sizes.append((sz, e))

sizes.sort(reverse=True)
print('Top 10 by size:')
for sz, name in sizes[:10]:
    mb = sz / (1024*1024)
    print('  %.2f MB - %s' % (mb, name[:60]))

total = sum(os.path.getsize(os.path.join(base, e)) for e in entries)
print('Total files1: %.2f MB (%d files)' % (total/(1024*1024), len(entries)))
