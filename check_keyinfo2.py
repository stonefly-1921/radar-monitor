import sqlite3
import os

key_db = r'C:\Users\15041\xwechat_files\all_users\login\wshjustin\key_info.db'
conn = sqlite3.connect(key_db)
c = conn.cursor()
c.execute("SELECT * FROM LoginKeyInfoTable")
rows = c.fetchall()
c.execute("PRAGMA table_info(LoginKeyInfoTable)")
cols = [col[1] for col in c.fetchall()]
print('Columns:', cols)
for row in rows:
    print()
    for i, (col, val) in enumerate(zip(cols, row)):
        if isinstance(val, bytes):
            print(f'  {col}: bytes({len(val)}) = {val.hex()[:100]}...')
        else:
            print(f'  {col}: {val}')
conn.close()
