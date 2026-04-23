import sqlite3
import os

db_path = r'C:\Users\15041\Desktop\wechat-decrypt\decrypted\message_0.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [t[0] for t in cursor.fetchall()]
print('Tables:', tables)

# Try to read messages
if 'message' in tables:
    cursor.execute("SELECT msgId, msgSeq, msgFromUsrName, msgToUsrName, strContent, createTime, msgType FROM message ORDER BY createTime DESC LIMIT 20")
    rows = cursor.fetchall()
    print('\nRecent messages:')
    for row in rows[:20]:
        print(f"  [{row[5]}] {row[2]} -> {row[3]}: {str(row[4])[:80]}")

conn.close()
