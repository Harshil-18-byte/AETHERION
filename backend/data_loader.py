"""
Data loader module — loads and preprocesses all CSV files from the data/ directory.

Actual CSV columns:
  symbol, datetime, expiry, CE, PE, spot_close, ATM, strike,
  oi_CE, oi_PE, volume_CE, volume_PE

We engineer additional features:
  - iv_proxy: (oi_CE + oi_PE) / spot_close
  - pcr: oi_PE / oi_CE  (Put-Call Ratio by OI)
  - volume_pcr: volume_PE / volume_CE
  - total_oi: oi_CE + oi_PE
  - total_volume: volume_CE + volume_PE
  - oi_change_CE / oi_change_PE: per-strike OI change over time
  - moneyness: strike / spot_close
"""

import os
import glob
import pandas as pd
import numpy as np


def load_data(data_dir: str = None) -> pd.DataFrame:
    """
    Load all CSVs from the data directory and return a single merged DataFrame
    with engineered features.
    """
    if data_dir is None:
        # Default: ../data relative to this file
        data_dir = os.path.join(os.path.dirname(__file__), "..", "data")

    csv_files = glob.glob(os.path.join(data_dir, "*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"No CSV files found in {data_dir}")

    frames = []
    for f in csv_files:
        try:
            df = pd.read_csv(f)
            frames.append(df)
        except Exception as e:
            print(f"[WARN] Skipping {f}: {e}")

    if not frames:
        raise ValueError("Could not load any CSV files")

    df = pd.concat(frames, ignore_index=True)

    # ── Parse dates ──────────────────────────────────────────────
    df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce")
    df["expiry"] = pd.to_datetime(df["expiry"], errors="coerce")

    # ── Drop rows with critical nulls ────────────────────────────
    df = df.dropna(subset=["datetime", "strike", "spot_close"])

    # ── Numeric coercion ─────────────────────────────────────────
    numeric_cols = ["CE", "PE", "spot_close", "ATM", "strike",
                    "oi_CE", "oi_PE", "volume_CE", "volume_PE"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.fillna(0)

    # ── Feature engineering ──────────────────────────────────────
    df["total_oi"] = df["oi_CE"] + df["oi_PE"]
    df["total_volume"] = df["volume_CE"] + df["volume_PE"]

    # Implied Volatility proxy
    df["iv_proxy"] = np.where(
        df["spot_close"] > 0,
        (df["oi_CE"] + df["oi_PE"]) / df["spot_close"],
        0,
    )

    # Put-Call Ratio (OI-based)
    df["pcr"] = np.where(
        df["oi_CE"] > 0,
        df["oi_PE"] / df["oi_CE"],
        np.nan,
    )

    # Volume Put-Call Ratio
    df["volume_pcr"] = np.where(
        df["volume_CE"] > 0,
        df["volume_PE"] / df["volume_CE"],
        np.nan,
    )

    # Moneyness
    df["moneyness"] = np.where(
        df["spot_close"] > 0,
        df["strike"] / df["spot_close"],
        np.nan,
    )

    # OI change per strike over time
    df = df.sort_values(["expiry", "strike", "datetime"])
    df["oi_change_CE"] = df.groupby(["expiry", "strike"])["oi_CE"].diff().fillna(0)
    df["oi_change_PE"] = df.groupby(["expiry", "strike"])["oi_PE"].diff().fillna(0)

    # Final sort
    df = df.sort_values("datetime").reset_index(drop=True)

    print(f"[INFO] Loaded {len(df):,} rows from {len(csv_files)} CSV files")
    print(f"[INFO] Date range: {df['datetime'].min()} → {df['datetime'].max()}")
    print(f"[INFO] Expiries: {sorted(df['expiry'].dropna().unique())}")

    return df
