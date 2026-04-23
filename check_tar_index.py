import os

# Read tar_index.dat to understand structure
root = r'C:\Users\15041\xwechat_files\backup\wshjustin\8b28002d18b0751decef2edc17ff6c20'
tar_index = os.path.join(root, 'tar_index.dat')

with open(tar_index, 'rb') as f:
    data = f.read()

print('tar_index.dat size:', len(data), 'bytes')
print('First 200 bytes (hex):')
print(data[:200].hex())
print()
print('First 200 bytes (ascii, non-printable as .):')
for i in range(min(200, len(data))):
    c = data[i]
    if 32 <= c < 127:
        print(chr(c), end='')
    else:
        print('.', end='')
print()
print()

# Also check backup.attr
backup_attr = os.path.join(root, 'backup.attr')
with open(backup_attr, 'rb') as f:
    attr_data = f.read()
print('backup.attr size:', len(attr_data), 'bytes')
print('backup.attr hex:')
print(attr_data.hex())
print()
print('backup.attr ascii:')
for i in range(len(attr_data)):
    c = attr_data[i]
    if 32 <= c < 127:
        print(chr(c), end='')
    else:
        print('.', end='')
print()
