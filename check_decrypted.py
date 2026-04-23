import sqlite3
import os

decrypted_dir = r'C:\Users\15041\Desktop\wechat-decrypt\decrypted'
for fname in os.listdir(decrypted_dir):
    fpath = os.path.join(decrypted_dir, fname)
    if os.path.isfile(fpath) and fname.endswith('.db'):
        with open(fpath, 'rb') as f:
            header = f.read(16)
        print(f'{fname}: header={header.hex()}, size={os.path.getsize(fpath)}')
        try:
            conn = sqlite3.connect(fpath)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [t[0] for t in cursor.fetchall()]
            print(f'  Tables: {tables[:10]}')
            if 'message' in tables:
                cursor.execute("SELECT COUNT(*) FROM message")
                count = cursor.fetchone()[0]
                print(f'  Message count: {count}')
            conn.close()
        except Exception as e:
            print(f'  Error: {e}')
