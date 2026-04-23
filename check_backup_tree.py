import os

root = r'C:\Users\15041\xwechat_files\backup\wshjustin\8b28002d18b0751decef2edc17ff6c20'
counts = {}
total_sz = 0
for dirpath, dirnames, filenames in os.walk(root):
    rel = os.path.relpath(dirpath, root)
    cnt = len(filenames)
    sz = 0
    for f in filenames:
        fp = os.path.join(dirpath, f)
        try:
            sz += os.path.getsize(fp)
        except:
            pass
    counts[rel] = (cnt, sz)
    total_sz += sz

print('Total size: %.2f GB' % (total_sz/(1024*1024*1024)))
print('Directory breakdown:')
for d, (cnt, sz) in sorted(counts.items()):
    mb = sz / (1024*1024)
    print('  %s: %d files, %.2f MB' % (d, cnt, mb))
