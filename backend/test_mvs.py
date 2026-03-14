from db.connection import get_connection
from db.schema import MATERIALIZED_VIEWS

conn = get_connection()
for name, sql in MATERIALIZED_VIEWS.items():
    print(f"Testing MV: {name}")
    try:
        conn.execute(f"DROP TABLE IF EXISTS {name}")
        conn.execute(sql)
        print(f"  ✅ SUCCESS: {name}")
    except Exception as e:
        print(f"  ❌ FAILED: {name} - {e}")
        print(f"  SQL: {sql}")
