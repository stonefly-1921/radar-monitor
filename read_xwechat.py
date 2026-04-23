import sqlite3
import os

db_dir = r'C:\Users\15041\xwechat_files\wshjustin_3dff\db_storage\message'
files = ['message_0.db', 'message_1.db', 'message_2.db', 'message_3.db']

for fname in files:
    db_path = os.path.join(db_dir, fname)
    if os.path.exists(db_path):
        size = os.path.getsize(db_path)
        print(f'\n=== {fname} ({size} bytes) ===')
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            print(f'Tables: {[t[0] for t in tables]}')
            conn.close()
        except Exception as e:
            print(f'Error: {e}')
    else:
        print(f'{fname} not found')
