import os
import sqlite3

decrypted_dir = r'C:\Users\15041\Desktop\wechat-decrypt\decrypted'
print('Files in decrypted dir:')
for f in os.listdir(decrypted_dir):
    fpath = os.path.join(decrypted_dir, f)
    if os.path.isfile(fpath):
        size = os.path.getsize(fpath)
        print(f'  {f}: {size} bytes')
        if size > 0:
            try:
                conn = sqlite3.connect(fpath)
                c = conn.cursor()
                c.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [t[0] for t in c.fetchall()]
                print(f'    Tables: {tables[:5]}')
                conn.close()
            except Exception as e:
                print(f'    Error: {e}')
