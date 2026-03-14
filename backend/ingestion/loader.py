import glob
import os
import pandas as pd
from db.connection import get_connection
from config import CSV_DATA_DIR


def load_csv_to_sqlite() -> int:
    """
    Scan CSV_DATA_DIR for *_exp.csv files and load them into options_raw.
    Returns the total number of rows loaded.
    """
    conn = get_connection()

    # Clear existing raw data
    conn.execute("DELETE FROM options_raw")

    pattern = os.path.join(CSV_DATA_DIR, "*_exp.csv")
    csv_files = sorted(glob.glob(pattern))

    if not csv_files:
        raise FileNotFoundError(
            f"No *_exp.csv files found in {CSV_DATA_DIR}. "
        )

    total_rows = 0
    for fpath in csv_files:
        fname = os.path.basename(fpath)
        
        # Load via Pandas since SQLite doesn't have native read_csv_auto
        df = pd.read_csv(fpath)
        df.columns = df.columns.str.lower()
        
        # Write to SQLite using SQLAlchemy engine
        from db.postgres import engine
        df.to_sql("options_raw", engine, if_exists="append", index=False)
        
        count = len(df)
        total_rows += count
        print(f"  [LOAD] {fname}: {count:,} rows")

    actual = conn.execute("SELECT COUNT(*) FROM options_raw").fetchone()[0]
    print(f"[LOAD] Total rows in options_raw: {actual:,}")
    return actual
