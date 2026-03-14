import sqlite3
print(f"sqlite3 version: {sqlite3.version}")
print(f"sqlite3.sqlite_version: {sqlite3.sqlite_version}")

conn = sqlite3.connect(":memory:")
cursor = conn.cursor()
try:
    cursor.execute("DROP TABLE IF EXISTS test")
    print("DROP TABLE IF EXISTS test: SUCCESS")
except Exception as e:
    print(f"DROP TABLE IF EXISTS test: FAILED - {e}")

try:
    cursor.execute("CREATE TABLE test (id INTEGER)")
    cursor.execute("DROP TABLE IF EXISTS test")
    print("DROP TABLE IF EXISTS test (with table): SUCCESS")
except Exception as e:
    print(f"DROP TABLE IF EXISTS test (with table): FAILED - {e}")
conn.close()
