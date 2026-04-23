import os

root = r'C:\Users\15041\xwechat_files\backup\wshjustin\8b28002d18b0751decef2edc17ff6c20'

# Check top-level files
print('=== Top-level files ===')
for f in ['backup.attr', 'alt_name.dat', 'pkg_info.dat', 'tar_index.dat', 'detail.dat', 'backup_time.dat', 'phone_history.dat', 'phoneid.dat', 'pkg.attr']:
    path = os.path.join(root, f)
    if os.path.exists(path):
        sz = os.path.getsize(path)
        print('  %s: %d bytes' % (f, sz))

# Count subdirs
print()
print('=== Subdirectories in files/1 ===')
files1 = os.path.join(root, r'files\1')
subdirs = [d for d in os.listdir(files1) if os.path.isdir(os.path.join(files1, d))]
print('  Total chat dirs: %d' % len(subdirs))

# Count total files across all subdirs
total_files = 0
total_size = 0
chatpkg_count = 0
media_count = 0
index_count = 0

for sd in subdirs:
    sdpath = os.path.join(files1, sd)
    for sub in ['ChatPackage', 'Index', 'Media']:
        subpath = os.path.join(sdpath, sub)
        if os.path.exists(subpath):
            for f in os.listdir(subpath):
                fp = os.path.join(subpath, f)
                if os.path.isfile(fp):
                    sz = os.path.getsize(fp)
                    total_files += 1
                    total_size += sz
                    if sub == 'ChatPackage':
                        chatpkg_count += 1
                    elif sub == 'Media':
                        media_count += 1
                    elif sub == 'Index':
                        index_count += 1

print('  ChatPackage files: %d' % chatpkg_count)
print('  Index files: %d' % index_count)
print('  Media files: %d' % media_count)
print('  Total files: %d' % total_files)
print('  Total size: %.2f GB' % (total_size / (1024**3)))
