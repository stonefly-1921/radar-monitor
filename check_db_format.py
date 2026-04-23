import os

# Check the file header of message_0.db
db_path = r'C:\Users\15041\xwechat_files\wshjustin_3dff\db_storage\message\message_0.db'
with open(db_path, 'rb') as f:
    header = f.read(16)
    print('Header bytes:', header.hex())
    print('Header text:', header.decode('utf-8', errors='replace'))

# Try SQLite
import sqlite3
try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print('Tables:', [t[0] for t in tables])
    conn.close()
except Exception as e:
    print('SQLite error:', e)

# Check if it's a EnMicroMsg.db format (WeChat's encrypted SQLite)
# WeChat stores message data in MSG0.db etc with device ID based encryption
print()
print('File size:', os.path.getsize(db_path), 'bytes')

# Check if it's the mobile backup format (iOS) 
# iOS backups use manifest.db and the actual dbs are in Manifest.db
manifest_path = os.path.join(os.path.dirname(db_path), '..', '..', 'Manifest.db')
if os.path.exists(manifest_path):
    print('Manifest.db exists')
else:
    print('No Manifest.db found')
