import sqlite3

path = r'C:\Users\15041\Documents\WeChat Files\wshjustin\Msg\Multi\MSG0.db'
conn = sqlite3.connect(path)
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cur.fetchall()
print("Tables:", [t[0] for t in tables])

# Try to read a bit from the first table
if tables:
    table_name = tables[0][0]
    cur.execute(f"SELECT COUNT(*) FROM {table_name}")
    print(f"Row count in {table_name}: {cur.fetchone()[0]}")
conn.close()
