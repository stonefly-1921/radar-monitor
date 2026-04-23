import sqlite3
import os

key_db = r'C:\Users\15041\xwechat_files\all_users\login\wshjustin\key_info.db'
conn = sqlite3.connect(key_db)
c = conn.cursor()
c.execute("SELECT key_info_data FROM LoginKeyInfoTable")
rows = c.fetchall()
conn.close()

known_salt = bytes.fromhex('0c60d940ad4890ed954927b20c051c4a')
known_key = bytes.fromhex('ce21fdd6ae57c1f23cc4ce3e315ff857138773906331833f7f30a8e613dfab16')

for i, row in enumerate(rows):
    d = row[0]
    print(f'Row {i} ({len(d)} bytes):')
    if known_salt in d:
        print(f'  -> Contains known salt for message_0.db! pos={d.index(known_salt)}')
    if known_key in d:
        print(f'  -> Contains known enc_key! pos={d.index(known_key)}')
    print(f'  Raw: {d.hex()[:200]}')
