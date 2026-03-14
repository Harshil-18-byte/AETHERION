"""
Analytics module — volatility pattern detection, heatmap data,
volatility surface, and PCR time series.
"""

import numpy as np
import pandas as pd
from scipy import stats


def compute_heatmap(df: pd.DataFrame, expiry: str = None) -> dict:
    """
    Strike × Expiry OI heatmap matrix.
    Returns {strikes: [...], expiries: [...], call_oi: [[...]], put_oi: [[...]], total_oi: [[...]]}
    """
    data = df.copy()
    if expiry:
        data = data[data["expiry"] == pd.to_datetime(expiry)]

    # Aggregate total OI per strike × expiry
    pivot_call = data.pivot_table(
        values="oi_ce", index="strike", columns="expiry", aggfunc="last"
    ).fillna(0)
    pivot_put = data.pivot_table(
        values="oi_pe", index="strike", columns="expiry", aggfunc="last"
    ).fillna(0)
    pivot_total = data.pivot_table(
        values="total_oi", index="strike", columns="expiry", aggfunc="last"
    ).fillna(0)

    strikes = [float(s) for s in pivot_total.index.tolist()]
    expiries = [str(e)[:10] for e in pivot_total.columns.tolist()]

    return {
        "strikes": strikes,
        "expiries": expiries,
        "call_oi": pivot_call.values.tolist(),
        "put_oi": pivot_put.values.tolist(),
        "total_oi": pivot_total.values.tolist(),
    }


def compute_volatility_surface(df: pd.DataFrame) -> dict:
    """
    IV proxy across strike & expiry — data for 3D surface plot.
    Returns {strikes, expiries, iv_values (2D matrix)}
    """
    pivot = df.pivot_table(
        values="iv_proxy", index="strike", columns="expiry", aggfunc="mean"
    ).fillna(0)

    strikes = [float(s) for s in pivot.index.tolist()]
    expiries = [str(e)[:10] for e in pivot.columns.tolist()]

    return {
        "strikes": strikes,
        "expiries": expiries,
        "iv_values": pivot.values.tolist(),
    }


def compute_pcr_timeseries(df: pd.DataFrame, expiry: str = None) -> list:
    """
    Put-Call Ratio over time — aggregated across all strikes.
    Returns [{datetime, pcr, volume_pcr}, ...]
    """
    data = df.copy()
    if expiry:
        data = data[data["expiry"] == pd.to_datetime(expiry)]

    grouped = data.groupby("datetime").agg(
        total_oi_ce=("oi_ce", "sum"),
        total_oi_pe=("oi_pe", "sum"),
        total_vol_ce=("volume_ce", "sum"),
        total_vol_pe=("volume_pe", "sum"),
    ).reset_index()

    grouped["pcr"] = np.where(
        grouped["total_oi_ce"] > 0,
        grouped["total_oi_pe"] / grouped["total_oi_ce"],
        None,
    )
    grouped["volume_pcr"] = np.where(
        grouped["total_vol_ce"] > 0,
        grouped["total_vol_pe"] / grouped["total_vol_ce"],
        None,
    )

    result = []
    for _, row in grouped.iterrows():
        result.append({
            "datetime": str(row["datetime"]),
            "pcr": None if row["pcr"] is None else round(float(row["pcr"]), 4),
            "volume_pcr": None if row["volume_pcr"] is None else round(float(row["volume_pcr"]), 4),
        })
    return result


def detect_volatility_skew(df: pd.DataFrame) -> list:
    """
    For each expiry + timestamp, compare IV at OTM puts vs OTM calls.
    Skew exists when Put IV >> Call IV.
    """
    results = []
    for expiry, exp_group in df.groupby("expiry"):
        latest = exp_group[exp_group["datetime"] == exp_group["datetime"].max()]
        if latest.empty:
            continue

        atm_strike = latest["ATM"].iloc[0]
        if atm_strike == 0:
            atm_strike = latest["spot_close"].iloc[0]

        otm_puts = latest[latest["strike"] < atm_strike]
        otm_calls = latest[latest["strike"] > atm_strike]

        avg_put_iv = otm_puts["iv_proxy"].mean() if len(otm_puts) > 0 else 0
        avg_call_iv = otm_calls["iv_proxy"].mean() if len(otm_calls) > 0 else 0

        skew_ratio = avg_put_iv / avg_call_iv if avg_call_iv > 0 else 0

        pattern = "Neutral"
        if skew_ratio > 1.3:
            pattern = "Negative Skew (Bearish / Fear)"
        elif skew_ratio < 0.7:
            pattern = "Positive Skew (Bullish)"

        results.append({
            "expiry": str(expiry)[:10],
            "atm_strike": float(atm_strike),
            "avg_put_iv": round(float(avg_put_iv), 4),
            "avg_call_iv": round(float(avg_call_iv), 4),
            "skew_ratio": round(float(skew_ratio), 4),
            "pattern": pattern,
        })

    return results


def detect_volatility_smile(df: pd.DataFrame) -> list:
    """
    Fit 2nd-degree polynomial to IV vs Strike curve.
    If curvature (coefficient of x²) > threshold → smile detected.
    """
    results = []
    for expiry, exp_group in df.groupby("expiry"):
        latest = exp_group[exp_group["datetime"] == exp_group["datetime"].max()]
        if len(latest) < 5:
            continue

        strikes = latest["strike"].values
        ivs = latest["iv_proxy"].values

        try:
            coeffs = np.polyfit(strikes, ivs, 2)
            curvature = coeffs[0]

            has_smile = bool(abs(curvature) > 1e-8)

            results.append({
                "expiry": str(expiry)[:10],
                "curvature": float(curvature),
                "has_smile": has_smile,
                "pattern": "Volatility Smile" if has_smile else "Flat/No Smile",
                "coefficients": [float(c) for c in coeffs],
            })
        except Exception:
            pass

    return results


def detect_iv_spikes(df: pd.DataFrame, z_threshold: float = 2.5) -> list:
    """
    Rolling Z-score on IV time-series. |Z-score| > threshold → spike.
    """
    results = []

    # Aggregate IV proxy per timestamp
    ts = df.groupby("datetime").agg(
        mean_iv=("iv_proxy", "mean"),
        spot=("spot_close", "first"),
    ).reset_index().sort_values("datetime")

    if len(ts) < 10:
        return results

    # Rolling z-score (window=20)
    window = min(20, len(ts) // 2)
    ts["rolling_mean"] = ts["mean_iv"].rolling(window=window, min_periods=3).mean()
    ts["rolling_std"] = ts["mean_iv"].rolling(window=window, min_periods=3).std()
    ts["z_score"] = (ts["mean_iv"] - ts["rolling_mean"]) / ts["rolling_std"].replace(0, np.nan)
    ts = ts.dropna(subset=["z_score"])

    spikes = ts[ts["z_score"].abs() > z_threshold]

    for _, row in spikes.iterrows():
        results.append({
            "datetime": str(row["datetime"]),
            "mean_iv": round(float(row["mean_iv"]), 4),
            "z_score": round(float(row["z_score"]), 4),
            "direction": "Spike UP" if row["z_score"] > 0 else "Spike DOWN",
            "spot_price": float(row["spot"]),
        })

    return results
