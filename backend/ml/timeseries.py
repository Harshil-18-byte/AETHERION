"""
Time-Series Analysis — rolling stats, trend detection, simple forecasting.
"""

import numpy as np
import pandas as pd
from db.connection import get_connection
from config import FORECAST_HORIZON, ROLLING_WINDOW_SHORT, ROLLING_WINDOW_LONG


def run_timeseries_analysis() -> dict:
    """
    Compute time-series features using SQLite and Pandas.
    """
    conn = get_connection()

    # Get bucketed data (5-minute windows)
    bucket_data = conn.execute("""
        SELECT
            expiry,
            date_trunc('minute', datetime) - (extract(minute from datetime)::int % 5) * interval '1 minute' AS bucket,
            AVG(iv_proxy) AS avg_iv,
            SUM(total_oi) AS total_oi,
            SUM(total_volume) AS total_vol
        FROM options_enriched
        GROUP BY expiry, bucket
        ORDER BY expiry, bucket
    """).df()
    
    # Cast decimals/numeric to float for numpy compatibility
    for col in ["avg_iv", "total_oi", "total_vol"]:
        if col in bucket_data.columns:
            bucket_data[col] = bucket_data[col].astype(float)

    if len(bucket_data) < 5:
        print("[TIMESERIES] Not enough data for time-series analysis, skipping")
        return {"iv_trends": [], "oi_trends": [], "volume_buildups": []}

    iv_trend_list = []
    oi_trend_list = []
    vol_buildup_list = []

    for exp in bucket_data["expiry"].unique():
        df_exp = bucket_data[bucket_data["expiry"] == exp].copy()
        df_exp["tick"] = range(len(df_exp))
        
        # 1. IV Trend
        if len(df_exp) > 1:
            z = np.polyfit(df_exp["tick"], df_exp["avg_iv"], 1)
            slope = float(z[0])
            # Simple R2 via correlation
            r2 = float(df_exp["avg_iv"].corr(df_exp["tick"])**2)
        else:
            slope, r2 = 0, 0
            
        direction = "FLAT"
        if slope > 0.01: direction = "RISING"
        elif slope < -0.01: direction = "FALLING"

        iv_trend_list.append({
            "expiry": str(exp)[:10],
            "direction": direction,
            "slope": round(float(slope), 6),
            "r2": round(r2, 4),
            "iv_range": [round(float(df_exp["avg_iv"].min()), 4), round(float(df_exp["avg_iv"].max()), 4)],
            "iv_mean": round(float(df_exp["avg_iv"].mean()), 4),
            "n_points": len(df_exp),
        })

        # 2. OI Trend
        oi_start = float(df_exp["total_oi"].iloc[0])
        oi_end = float(df_exp["total_oi"].iloc[-1])
        pct_change = ((oi_end - oi_start) / oi_start * 100) if oi_start > 0 else 0
        
        if len(df_exp) > 1:
            z_oi = np.polyfit(df_exp["tick"], df_exp["total_oi"], 1)
            oi_slope = float(z_oi[0])
        else:
            oi_slope = 0
            
        oi_direction = "STABLE"
        if oi_slope > 0: oi_direction = "BUILDUP"
        elif oi_slope < 0: oi_direction = "UNWINDING"

        oi_trend_list.append({
            "expiry": str(exp)[:10],
            "direction": oi_direction,
            "oi_change_pct": round(pct_change, 2),
            "oi_start": round(oi_start, 0),
            "oi_end": round(oi_end, 0),
            "n_points": len(df_exp),
        })

        # 3. Volume Buildup
        recent = df_exp["total_vol"].tail(5).mean()
        overall = df_exp["total_vol"].mean()
        ratio = recent / overall if overall > 0 else 1
        
        signal = "NORMAL"
        if ratio > 1.5: signal = "STRONG_BUILDUP"
        elif ratio > 1.1: signal = "MODERATE_BUILDUP"
        elif ratio < 0.5: signal = "DRYING_UP"

        vol_buildup_list.append({
            "expiry": str(exp)[:10],
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
