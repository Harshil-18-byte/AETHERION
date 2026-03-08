"""
DuckDB connection manager — singleton with thread-safe access.

Usage:
    conn = get_connection()     # returns the shared connection
    close_connection()          # shutdown cleanup
"""

import duckdb
import threading
from config import DUCKDB_PATH

_lock = threading.Lock()
_connection: duckdb.DuckDBPyConnection | None = None


def get_connection() -> duckdb.DuckDBPyConnection:
    """Return the shared DuckDB connection, creating it on first call."""
    global _connection
    if _connection is None:
        with _lock:
            if _connection is None:
                _connection = duckdb.connect(database=DUCKDB_PATH)
                # Enable progress bar for long queries
                _connection.execute("SET enable_progress_bar = true")
                print(f"[DB] Connected to DuckDB ({DUCKDB_PATH})")
    return _connection


def close_connection() -> None:
    """Close the shared connection (call at shutdown)."""
    global _connection
    if _connection is not None:
        with _lock:
            if _connection is not None:
                _connection.close()
                _connection = None
                print("[DB] Connection closed")
