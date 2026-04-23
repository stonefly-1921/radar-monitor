import sqlite3
import os

decrypted_dir = r'C:\Users\15041\Desktop\wechat-decrypt\decrypted'
session_path = os.path.join(decrypted_dir, 'session.db')

# Check if decrypted session.db exists
if os.path.exists(session_path) and os.path.getsize(session_path) > 0:
    print(f'session.db size: {os.path.getsize(session_path)}')
    conn = sqlite3.connect(session_path)
    c = conn.cursor()
    c.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [t[0] for t in c.fetchall()]
    print(f'Tables: {tables}')
    conn.close()
else:
    print('session.db not found or empty in decrypted folder')
    # Check original
    orig = r'C:\Users\15041\xwechat_files\wshjustin_3dff\db_storage\session\session.db'
    if os.path.exists(orig):
        print(f'Original session.db size: {os.path.getsize(orig)}')
