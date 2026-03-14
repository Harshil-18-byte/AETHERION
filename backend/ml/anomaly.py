"""
Anomaly Detection — Isolation Forest + Z-score based flagging.
Results are written back into DuckDB (options_enriched).
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from db.connection import get_connection
from config import (
    ISOLATION_FOREST_CONTAMINATION,
    ISOLATION_FOREST_N_ESTIMATORS,
    ZSCORE_THRESHOLD,
    VOLUME_SPIKE_STDDEV_MULT,
)


def run_anomaly_detection() -> dict:
    """
    1. Pull feature vectors from DuckDB
    2. Run Isolation Forest
    3. Compute Z-score anomaly flags
    4. Compute unusual activity scores
    5. Write results back to DuckDB
    Returns summary stats.
    """
    conn = get_connection()

    # ── Pull feature matrix ──────────────────────────────────────
    df = conn.execute("""
        SELECT id, volume_ce, volume_pe, oi_ce, oi_pe,
               iv_proxy, total_volume, total_oi,
               relative_volume, oi_change_pct, volume_change_pct
        FROM options_enriched
    """).df()

    # Cast decimals to float for scikit-learn
    numeric_cols = ["volume_ce", "volume_pe", "oi_ce", "oi_pe", "iv_proxy", "total_volume", "total_oi", "relative_volume", "oi_change_pct", "volume_change_pct"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = df[col].astype(float)

    if len(df) < 20:
        print("[ANOMALY] Not enough data for anomaly detection, skipping")
        return {"total": 0, "iso_forest": 0, "z_score": 0}

    feature_cols = [
        "volume_ce", "volume_pe", "oi_ce", "oi_pe",
        "iv_proxy", "relative_volume",
    ]
    X = df[feature_cols].fillna(0).values

    # ── Isolation Forest ─────────────────────────────────────────
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    iso_model = IsolationForest(
        contamination=ISOLATION_FOREST_CONTAMINATION,
        n_estimators=ISOLATION_FOREST_N_ESTIMATORS,
        random_state=42,
    )
    preds = iso_model.fit_predict(X_scaled)       # -1 = anomaly
    scores = iso_model.decision_function(X_scaled) # lower = more anomalous

    df["iso_flag"] = (preds == -1).astype(int)
    df["iso_score"] = scores

    # ── Z-score anomaly (volume spikes) ──────────────────────────
    vol_mean = df["total_volume"].mean()
    vol_std = df["total_volume"].std()
    if vol_std > 0:
        df["vol_zscore"] = (df["total_volume"] - vol_mean) / vol_std
    else:
        df["vol_zscore"] = 0.0

    df["z_flag"] = (df["vol_zscore"].abs() > ZSCORE_THRESHOLD).astype(int)

    # ── IV Z-score ───────────────────────────────────────────────
    iv_mean = df["iv_proxy"].mean()
    iv_std = df["iv_proxy"].std()
    if iv_std > 0:
        df["iv_zscore"] = (df["iv_proxy"] - iv_mean) / iv_std
    else:
        df["iv_zscore"] = 0.0

    # ── Combined anomaly flag ────────────────────────────────────
    df["anomaly_flag"] = ((df["iso_flag"] == 1) | (df["z_flag"] == 1)).astype(int)
    df["anomaly_score"] = df["iso_score"]

    # ── Unusual activity scoring (0-1 scale) ─────────────────────
    # Combines: relative volume, |vol_zscore|, |iv_zscore|
    rv_norm = np.clip(df["relative_volume"].fillna(1) / 5.0, 0, 1)
    vz_norm = np.clip(df["vol_zscore"].abs() / 5.0, 0, 1)
    iz_norm = np.clip(df["iv_zscore"].abs() / 5.0, 0, 1)
    df["unusual_activity_score"] = (
        0.4 * rv_norm + 0.35 * vz_norm + 0.25 * iz_norm
    ).round(4)

    # ── Write back to DuckDB ─────────────────────────────────────
    update_df = df[["id", "anomaly_flag", "anomaly_score", "unusual_activity_score"]]

    # Register as a temporary table
    conn.register("_anomaly_results", update_df)
    
    # Add index for faster update
    conn.execute("CREATE INDEX IF NOT EXISTS idx_temp_anomaly_id ON _anomaly_results(id)")
    
    # UPDATE via subquery
    conn.execute("""
        UPDATE options_enriched
        SET anomaly_flag = (
            SELECT ar.anomaly_flag FROM _anomaly_results ar WHERE ar.id = options_enriched.id
        ),
        anomaly_score = (
            SELECT ar.anomaly_score FROM _anomaly_results ar WHERE ar.id = options_enriched.id
        ),
        unusual_activity_score = (
            SELECT ar.unusual_activity_score FROM _anomaly_results ar WHERE ar.id = options_enriched.id
        )
        WHERE EXISTS (
            SELECT 1 FROM _anomaly_results ar WHERE ar.id = options_enriched.id
        )
    """)
    conn.unregister("_anomaly_results")

    n_anomalies = int(df["anomaly_flag"].sum())
    iso_count = int(df["iso_flag"].sum())
    z_count = int(df["z_flag"].sum())

    summary = {
        "total_rows": len(df),
        "iso_forest_anomalies": iso_count,
        "z_score_anomalies": z_count,
        "combined_anomalies": n_anomalies,
        "contamination": ISOLATION_FOREST_CONTAMINATION,
        "z_threshold": ZSCORE_THRESHOLD,
    }

    print(f"[ANOMALY] Isolation Forest: {iso_count:,} anomalies  |  "
          f"Z-score: {z_count:,}  |  Combined: {n_anomalies:,} ✅")

    return summary
