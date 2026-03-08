"""
Time-Series Analysis — rolling stats, trend detection, simple forecasting.
"""

import numpy as np
import pandas as pd
from db.connection import get_connection
from config import FORECAST_HORIZON, ROLLING_WINDOW_SHORT, ROLLING_WINDOW_LONG


def run_timeseries_analysis() -> dict:
    """
    Compute time-series features:
      - Rolling window averages / std devs (already in materialized view)
      - Trend detection on IV and OI
      - Simple linear extrapolation forecasts
    Returns summary dict with detected trends.
    """
    conn = get_connection()

    # ────────────────────────────────────────────────────────────
    # 1. IV TREND DETECTION per expiry
    #    Fit a simple linear slope to the last N IV observations.
    # ────────────────────────────────────────────────────────────
    iv_trends = conn.execute("""
        WITH per_bucket AS (
            SELECT
                expiry,
                time_bucket(INTERVAL '5 minutes', datetime) AS bucket,
                AVG(iv_proxy) AS avg_iv,
                ROW_NUMBER() OVER (PARTITION BY expiry ORDER BY time_bucket(INTERVAL '5 minutes', datetime)) AS tick
            FROM options_enriched
            GROUP BY expiry, time_bucket(INTERVAL '5 minutes', datetime)
        ),
        slope_calc AS (
            SELECT
                expiry,
                REGR_SLOPE(avg_iv, tick) AS iv_slope,
                REGR_R2(avg_iv, tick)    AS iv_r2,
                COUNT(*)                 AS n_points,
                MIN(avg_iv) AS iv_min,
                MAX(avg_iv) AS iv_max,
                AVG(avg_iv) AS iv_mean
            FROM per_bucket
            GROUP BY expiry
        )
        SELECT * FROM slope_calc ORDER BY expiry
    """).df()

    iv_trend_list = []
    for _, row in iv_trends.iterrows():
        slope = row["iv_slope"] if pd.notna(row["iv_slope"]) else 0
        if slope > 0.01:
            direction = "RISING"
        elif slope < -0.01:
            direction = "FALLING"
        else:
            direction = "FLAT"
        iv_trend_list.append({
            "expiry": str(row["expiry"])[:10],
            "direction": direction,
            "slope": round(float(slope), 6),
            "r2": round(float(row["iv_r2"]) if pd.notna(row["iv_r2"]) else 0, 4),
            "iv_range": [round(float(row["iv_min"]), 4), round(float(row["iv_max"]), 4)],
            "iv_mean": round(float(row["iv_mean"]), 4),
            "n_points": int(row["n_points"]),
        })

    # ────────────────────────────────────────────────────────────
    # 2. OI BUILDUP / DEPLETION detection
    # ────────────────────────────────────────────────────────────
    oi_trends = conn.execute("""
        WITH per_bucket AS (
            SELECT
                expiry,
                time_bucket(INTERVAL '5 minutes', datetime) AS bucket,
                SUM(total_oi) AS total_oi,
                ROW_NUMBER() OVER (PARTITION BY expiry ORDER BY time_bucket(INTERVAL '5 minutes', datetime)) AS tick
            FROM options_enriched
            GROUP BY expiry, time_bucket(INTERVAL '5 minutes', datetime)
        ),
        slope_calc AS (
            SELECT
                expiry,
                REGR_SLOPE(total_oi, tick) AS oi_slope,
                FIRST(total_oi ORDER BY tick ASC)  AS oi_start,
                LAST(total_oi ORDER BY tick DESC)  AS oi_end,
                COUNT(*) AS n_points
            FROM per_bucket
            GROUP BY expiry
        )
        SELECT * FROM slope_calc ORDER BY expiry
    """).df()

    oi_trend_list = []
    for _, row in oi_trends.iterrows():
        slope = row["oi_slope"] if pd.notna(row["oi_slope"]) else 0
        oi_start = float(row["oi_start"])
        oi_end = float(row["oi_end"])
        pct_change = ((oi_end - oi_start) / oi_start * 100) if oi_start > 0 else 0

        if slope > 0:
            direction = "BUILDUP"
        elif slope < 0:
            direction = "UNWINDING"
        else:
            direction = "STABLE"

        oi_trend_list.append({
            "expiry": str(row["expiry"])[:10],
            "direction": direction,
            "oi_change_pct": round(pct_change, 2),
            "oi_start": round(oi_start, 0),
            "oi_end": round(oi_end, 0),
            "n_points": int(row["n_points"]),
        })

    # ────────────────────────────────────────────────────────────
    # 3. VOLUME BUILDUP detection (last N vs overall)
    # ────────────────────────────────────────────────────────────
    vol_buildups = conn.execute("""
        WITH bucketed AS (
            SELECT
                expiry,
                time_bucket(INTERVAL '5 minutes', datetime) AS bucket,
                SUM(total_volume) AS bucket_vol
            FROM options_enriched
            GROUP BY expiry, time_bucket(INTERVAL '5 minutes', datetime)
        ),
        ranked AS (
            SELECT *,
                   ROW_NUMBER() OVER (PARTITION BY expiry ORDER BY bucket DESC) AS rn,
                   COUNT(*) OVER (PARTITION BY expiry) AS total_buckets
            FROM bucketed
        )
        SELECT
            expiry,
            AVG(CASE WHEN rn <= 5 THEN bucket_vol END) AS recent_avg,
            AVG(bucket_vol)                              AS overall_avg
        FROM ranked
        GROUP BY expiry
        ORDER BY expiry
    """).df()

    vol_buildup_list = []
    for _, row in vol_buildups.iterrows():
        recent = float(row["recent_avg"]) if pd.notna(row["recent_avg"]) else 0
        overall = float(row["overall_avg"]) if pd.notna(row["overall_avg"]) else 1
        ratio = recent / overall if overall > 0 else 1

        if ratio > 1.5:
            signal = "STRONG_BUILDUP"
        elif ratio > 1.1:
            signal = "MODERATE_BUILDUP"
        elif ratio < 0.5:
            signal = "DRYING_UP"
        else:
            signal = "NORMAL"

        vol_buildup_list.append({
            "expiry": str(row["expiry"])[:10],
            "signal": signal,
            "recent_vs_avg_ratio": round(ratio, 2),
        })

    summary = {
        "iv_trends": iv_trend_list,
        "oi_trends": oi_trend_list,
        "volume_buildups": vol_buildup_list,
    }

    print(f"[TIMESERIES] Trends computed: {len(iv_trend_list)} IV, "
          f"{len(oi_trend_list)} OI, {len(vol_buildup_list)} Volume ✅")

    return summary
