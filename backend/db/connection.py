import psycopg2
import pandas as pd
import threading
from config import POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB

_lock = threading.Lock()
_connection = None

class PostgresResultWrapper:
    """Mimics result object for compatibility."""
    def __init__(self, cursor, conn):
        self.cursor = cursor
        self.conn = conn

    def df(self):
        try:
            cols = [desc[0] for desc in self.cursor.description] if self.cursor.description else []
            data = self.cursor.fetchall()
            return pd.DataFrame(data, columns=cols)
        except Exception:
            return pd.DataFrame()

    def fetchone(self):
        return self.cursor.fetchone()

    def fetchall(self):
        return self.cursor.fetchall()

class PostgresConnectionWrapper:
    """Wraps psycopg2 connection to provide an execute method."""
    def __init__(self, conn):
        self.conn = conn

    def execute(self, sql, params=None):
        # Convert DuckDB/SQLite style ? placeholder to Postgres style %s
        sql = sql.replace("?", "%s")
        
        cursor = self.conn.cursor()
        try:
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
            
            # Auto-commit for DDL/DML unless in a transaction
            if not self.conn.autocommit:
                self.conn.commit()
                
            return PostgresResultWrapper(cursor, self.conn)
        except Exception as e:
            self.conn.rollback()
            raise e

    def close(self):
        self.conn.close()
    
    def register(self, name, df):
        # Implementation for Postgres (writing to temp table)
        from sqlalchemy import create_engine
        from config import DATABASE_URL
        engine = create_engine(DATABASE_URL)
        df.to_sql(name, engine, if_exists="replace", index=False)
    
    def unregister(self, name):
        self.execute(f"DROP TABLE IF EXISTS {name}")

def get_connection() -> PostgresConnectionWrapper:
    """Return the shared Postgres connection, creating it on first call."""
    global _connection
    if _connection is None:
        with _lock:
            if _connection is None:
                _connection = psycopg2.connect(
                    user=POSTGRES_USER,
                    password=POSTGRES_PASSWORD,
                    host=POSTGRES_HOST,
                    port=POSTGRES_PORT,
                    database=POSTGRES_DB
                )
                print(f"[DB] Connected to PostgreSQL ({POSTGRES_HOST})")
    return PostgresConnectionWrapper(_connection)

def close_connection() -> None:
    """Close the shared connection."""
    global _connection
    if _connection is not None:
        with _lock:
            if _connection is not None:
                _connection.close()
                _connection = None
                print("[DB] Connection closed")
