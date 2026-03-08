import sqlite3
import pandas as pd
import threading
from config import ANALYTICS_DB_PATH

_lock = threading.Lock()
_connection: sqlite3.Connection | None = None

class SQLiteResultWrapper:
    """Mimics DuckDB result object for compatibility."""
    def __init__(self, cursor, conn):
        self.cursor = cursor
        self.conn = conn

    def df(self):
        # Fallback to pandas for dataframe conversion
        # This is slower than DuckDB but necessary for SQLite
        try:
            # Get column names from cursor description
            cols = [desc[0] for desc in self.cursor.description] if self.cursor.description else []
            data = self.cursor.fetchall()
            return pd.DataFrame(data, columns=cols)
        except Exception:
            return pd.DataFrame()

    def fetchone(self):
        return self.cursor.fetchone()

    def fetchall(self):
        return self.cursor.fetchall()

class SQLiteConnectionWrapper:
    """Wraps sqlite3.Connection to provide an execute method like DuckDB."""
    def __init__(self, conn):
        self.conn = conn

    def execute(self, sql, params=None):
        cursor = self.conn.cursor()
        if params:
            # Convert DuckDB-style ?::DATE or ?::TIMESTAMP to ?
            sql = sql.replace("?::DATE", "?").replace("?::TIMESTAMP", "?").replace("?::DOUBLE", "?")
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)
        return SQLiteResultWrapper(cursor, self.conn)

    def close(self):
        self.conn.close()
    
    def register(self, name, df):
        # Mimics DuckDB's register to allow direct DF usage in SQL
        # In SQLite, we write the DF to a temp table
        df.to_sql(name, self.conn, if_exists="replace", index=False)
    
    def unregister(self, name):
        # Drops the temp table created by register
        self.conn.execute(f"DROP TABLE IF EXISTS {name}")

def get_connection() -> SQLiteConnectionWrapper:
    """Return the shared SQLite connection, creating it on first call."""
    global _connection
    if _connection is None:
        with _lock:
            if _connection is None:
                _connection = sqlite3.connect(ANALYTICS_DB_PATH, check_same_thread=False)
                print(f"[DB] Connected to SQLite ({ANALYTICS_DB_PATH})")
    return SQLiteConnectionWrapper(_connection)


def close_connection() -> None:
    """Close the shared connection (call at shutdown)."""
    global _connection
    if _connection is not None:
        with _lock:
            if _connection is not None:
                _connection.close()
                _connection = None
                print("[DB] Connection closed")
