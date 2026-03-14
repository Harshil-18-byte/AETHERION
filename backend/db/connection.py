import pandas as pd
import threading
import time
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from config import DATABASE_URL

_lock = threading.Lock()
_engine = None

class SQLiteResultWrapper:
    """Mimics result object for compatibility."""
    def __init__(self, result):
        self.result = result

    def df(self):
        try:
            return pd.DataFrame(self.result.fetchall(), columns=self.result.keys())
        except Exception:
            return pd.DataFrame()

    def fetchone(self):
        row = self.result.fetchone()
        return row if row else None

    def fetchall(self):
        return self.result.fetchall()

class SQLiteConnectionWrapper:
    """Wraps SQLAlchemy connection to provide an execute method with retries."""
    def __init__(self, engine):
        self.engine = engine

    def execute(self, sql, params=None, retries=3, delay=1.0):
        last_error = None
        for attempt in range(retries):
            try:
                # Use engine.begin() for a transactional context manager
                # This ensures the connection is closed/returned to the pool properly.
                with self.engine.connect() as conn:
                    # SQLAlchemy does not accept list parameters
                    if isinstance(params, list):
                        params = tuple(params)
                    
                    if params:
                        result = conn.exec_driver_sql(sql, params)
                    else:
                        result = conn.exec_driver_sql(sql.strip())
                    return SQLiteResultWrapper(result)
            except OperationalError as e:
                if "database is locked" in str(e).lower():
                    last_error = e
                    print(f"  [DB] Lock detected (attempt {attempt+1}/{retries}), retrying in {delay}s...")
                    time.sleep(delay)
                    continue
                raise e
            except Exception as e:
                print("❌ SQL Error:", e)
                print("Statement:", sql)
                print("Params:", params)
                raise e
        
        print(f"  ❌ Failed after {retries} retries: {last_error}")
        raise last_error

    def close(self):
        pass # Engine handles connections
    
    def register(self, name, df):
        # To avoid locking, we must use a single connection for the transaction.
        with self.engine.begin() as conn:
            df.to_sql(name, conn, if_exists="replace", index=False)
    
    def unregister(self, name):
        self.execute(f"DROP TABLE IF EXISTS {name}")

def get_engine():
    """Return the shared SQLAlchemy engine."""
    global _engine
    if _engine is None:
        with _lock:
            if _engine is None:
                _engine = create_engine(
                    DATABASE_URL,
                    connect_args={"check_same_thread": False, "timeout": 30},
                    pool_pre_ping=True
                )
                print(f"[DB] Initialized SQLite Engine ({DATABASE_URL})")
    return _engine

def get_connection() -> SQLiteConnectionWrapper:
    """Return the shared SQLite wrapper."""
    return SQLiteConnectionWrapper(get_engine())

def close_connection() -> None:
    pass
