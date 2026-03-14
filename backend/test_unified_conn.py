import pandas as pd
from db.connection import get_connection

print("Attempting to get connection...")
conn = get_connection()
print("Success!")

print("Running raw SQL...")
conn.execute("CREATE TABLE IF NOT EXISTS test_table (id INTEGER PRIMARY KEY, val TEXT)")
conn.execute("INSERT INTO test_table (val) VALUES (?)", ["test_value"])
res = conn.execute("SELECT * FROM test_table").df()
print("Raw SQL results:")
print(res)

print("Running df.to_sql (register)...")
df = pd.DataFrame({"a": [1, 2], "b": ["x", "y"]})
conn.register("temp_test", df)
res2 = conn.execute("SELECT * FROM temp_test").df()
print("df.to_sql results:")
print(res2)

print("Cleaning up...")
conn.unregister("temp_test")
conn.execute("DROP TABLE test_table")
print("Done!")
