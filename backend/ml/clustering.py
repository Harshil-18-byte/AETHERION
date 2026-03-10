"""
Clustering — K-Means + DBSCAN on strike-level features.
Results are stored back in DuckDB.
"""

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans, DBSCAN
from sklearn.preprocessing import StandardScaler
from db.connection import get_connection
from config import KMEANS_N_CLUSTERS, DBSCAN_EPS, DBSCAN_MIN_SAMPLES


def run_clustering() -> dict:
    """
    Cluster the latest snapshot per (strike, expiry) using:
      1. K-Means   → cluster_kmeans
      2. DBSCAN    → cluster_dbscan
    Store labels in options_enriched for all rows matching each (strike, expiry).
    """
    conn = get_connection()

    # Use the latest observation per (strike, expiry)
    df = conn.execute("""
        WITH latest AS (
            SELECT expiry, MAX(datetime) AS max_dt
            FROM options_enriched GROUP BY expiry
        )
        SELECT e.id, e.strike, e.expiry, e.total_volume, e.total_oi,
               e.iv_proxy, e.moneyness, e.days_to_expiry,
               e.relative_volume, e.pcr_oi
        FROM options_enriched e
        JOIN latest l ON e.expiry = l.expiry AND e.datetime = l.max_dt
    """).df()

    # Cast decimals to float
    numeric_cols = ["total_volume", "total_oi", "iv_proxy", "moneyness", "days_to_expiry", "relative_volume", "pcr_oi"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = df[col].astype(float)

    if len(df) < KMEANS_N_CLUSTERS:
        print("[CLUSTER] Not enough data for clustering, skipping")
        return {"kmeans_clusters": 0, "dbscan_clusters": 0}

    feature_cols = [
        "strike", "total_volume", "total_oi",
        "iv_proxy", "moneyness",
    ]
    X = df[feature_cols].fillna(0).values

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # ── K-Means ──────────────────────────────────────────────────
    n_clusters = min(KMEANS_N_CLUSTERS, len(df))
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    df["cluster_kmeans"] = kmeans.fit_predict(X_scaled)

    # ── DBSCAN ───────────────────────────────────────────────────
    dbscan = DBSCAN(eps=DBSCAN_EPS, min_samples=DBSCAN_MIN_SAMPLES)
    df["cluster_dbscan"] = dbscan.fit_predict(X_scaled)

    # ── Write labels back to DuckDB ──────────────────────────────
    # Update all rows for matching (strike, expiry),
    # not just the latest snapshot — so every timestamp gets labeled.
    update_df = df[["strike", "expiry", "cluster_kmeans", "cluster_dbscan"]].drop_duplicates()
    conn.register("_cluster_labels", update_df)
    conn.execute("""
        UPDATE options_enriched
        SET cluster_kmeans = (
            SELECT cl.cluster_kmeans FROM _cluster_labels cl 
            WHERE cl.strike = options_enriched.strike AND cl.expiry = options_enriched.expiry
        ),
        cluster_dbscan = (
            SELECT cl.cluster_dbscan FROM _cluster_labels cl 
            WHERE cl.strike = options_enriched.strike AND cl.expiry = options_enriched.expiry
        )
        WHERE EXISTS (
            SELECT 1 FROM _cluster_labels cl 
            WHERE cl.strike = options_enriched.strike AND cl.expiry = options_enriched.expiry
        )
    """)
    conn.unregister("_cluster_labels")

    n_kmeans = int(df["cluster_kmeans"].nunique())
    n_dbscan = int(df["cluster_dbscan"].nunique())

    # Build cluster summaries
    km_summary = []
    for c in range(n_clusters):
        subset = df[df["cluster_kmeans"] == c]
        avg_vol = subset["total_volume"].mean()
        overall_avg = df["total_volume"].mean()
        if avg_vol > overall_avg * 1.5:
            level = "High Activity"
        elif avg_vol > overall_avg * 0.5:
            level = "Medium Activity"
        else:
            level = "Low Activity"

        km_summary.append({
            "cluster_id": int(c),
            "activity_level": level,
            "count": int(len(subset)),
            "avg_strike": round(float(subset["strike"].mean()), 2),
            "strike_range": [float(subset["strike"].min()), float(subset["strike"].max())],
            "avg_volume": round(float(avg_vol), 0),
            "avg_oi": round(float(subset["total_oi"].mean()), 0),
            "avg_iv": round(float(subset["iv_proxy"].mean()), 4),
        })

    summary = {
        "kmeans_clusters": n_kmeans,
        "dbscan_clusters": n_dbscan,
        "dbscan_noise_points": int((df["cluster_dbscan"] == -1).sum()),
        "kmeans_summary": sorted(km_summary, key=lambda x: x["avg_volume"], reverse=True),
    }

    print(f"[CLUSTER] K-Means: {n_kmeans} clusters  |  "
          f"DBSCAN: {n_dbscan} clusters ({summary['dbscan_noise_points']} noise) ✅")

    return summary
