"""
AI/ML models module — Anomaly detection and clustering.
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler


def detect_anomalies(df: pd.DataFrame, contamination: float = 0.05) -> list:
    """
    Isolation Forest on [volume_CE, volume_PE, oi_CE, oi_PE, iv_proxy] columns.
    Returns list of anomaly rows with details.
    """
    feature_cols = ["volume_CE", "volume_PE", "oi_CE", "oi_PE", "iv_proxy"]
    features = df[feature_cols].fillna(0).values

    if len(features) < 10:
        return []

    scaler = StandardScaler()
    features_scaled = scaler.fit_transform(features)

    model = IsolationForest(
        contamination=contamination,
        random_state=42,
        n_estimators=100,
    )
    predictions = model.fit_predict(features_scaled)
    scores = model.decision_function(features_scaled)

    df_result = df.copy()
    df_result["anomaly"] = predictions       # -1 = anomaly, 1 = normal
    df_result["anomaly_score"] = scores      # lower = more anomalous

    anomalies = df_result[df_result["anomaly"] == -1]

    results = []
    for _, row in anomalies.iterrows():
        # Determine likely reason
        reasons = []
        if row["volume_CE"] + row["volume_PE"] > df["total_volume"].quantile(0.95):
            reasons.append("Unusually high volume")
        if row["oi_CE"] + row["oi_PE"] > df["total_oi"].quantile(0.95):
            reasons.append("Unusually high OI")
        if row["iv_proxy"] > df["iv_proxy"].quantile(0.95):
            reasons.append("High IV proxy")
        if abs(row.get("oi_change_CE", 0)) > df["oi_change_CE"].abs().quantile(0.95):
            reasons.append("Large CE OI change")
        if abs(row.get("oi_change_PE", 0)) > df["oi_change_PE"].abs().quantile(0.95):
            reasons.append("Large PE OI change")

        if not reasons:
            reasons.append("Statistical outlier")

        results.append({
            "datetime": str(row["datetime"]),
            "expiry": str(row["expiry"])[:10] if pd.notna(row["expiry"]) else None,
            "strike": float(row["strike"]),
            "spot_close": float(row["spot_close"]),
            "volume_CE": float(row["volume_CE"]),
            "volume_PE": float(row["volume_PE"]),
            "oi_CE": float(row["oi_CE"]),
            "oi_PE": float(row["oi_PE"]),
            "iv_proxy": round(float(row["iv_proxy"]), 4),
            "anomaly_score": round(float(row["anomaly_score"]), 4),
            "reasons": reasons,
        })

    # Sort by most anomalous first
    results.sort(key=lambda x: x["anomaly_score"])

    return results


def cluster_market_activity(df: pd.DataFrame, n_clusters: int = 4) -> dict:
    """
    K-Means clustering on Strike × Volume × OI to identify activity zones.
    Returns cluster labels and cluster summaries.
    """
    feature_cols = ["strike", "total_volume", "total_oi", "iv_proxy"]

    # Use latest snapshot per strike per expiry
    latest = df.sort_values("datetime").groupby(["expiry", "strike"]).last().reset_index()

    features = latest[feature_cols].fillna(0).values

    if len(features) < n_clusters:
        return {"clusters": [], "summary": []}

    scaler = StandardScaler()
    features_scaled = scaler.fit_transform(features)

    model = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    labels = model.fit_predict(features_scaled)

    latest["cluster"] = labels

    # Build per-cluster summary
    cluster_summaries = []
    for c in range(n_clusters):
        cluster_data = latest[latest["cluster"] == c]

        # Determine activity level
        avg_vol = cluster_data["total_volume"].mean()
        avg_oi = cluster_data["total_oi"].mean()
        overall_avg_vol = latest["total_volume"].mean()

        if avg_vol > overall_avg_vol * 1.5:
            activity_level = "High Activity (Hotspot)"
        elif avg_vol > overall_avg_vol * 0.5:
            activity_level = "Medium Activity"
        else:
            activity_level = "Low Activity"

        cluster_summaries.append({
            "cluster_id": int(c),
            "activity_level": activity_level,
            "count": int(len(cluster_data)),
            "avg_strike": round(float(cluster_data["strike"].mean()), 2),
            "strike_range": [float(cluster_data["strike"].min()), float(cluster_data["strike"].max())],
            "avg_volume": round(float(avg_vol), 2),
            "avg_oi": round(float(avg_oi), 2),
            "avg_iv_proxy": round(float(cluster_data["iv_proxy"].mean()), 4),
        })

    # Sort by activity (highest first)
    cluster_summaries.sort(key=lambda x: x["avg_volume"], reverse=True)

    # Build per-point data for frontend scatter plots
    cluster_points = []
    for _, row in latest.iterrows():
        cluster_points.append({
            "strike": float(row["strike"]),
            "expiry": str(row["expiry"])[:10] if pd.notna(row["expiry"]) else None,
            "total_volume": float(row["total_volume"]),
            "total_oi": float(row["total_oi"]),
            "iv_proxy": round(float(row["iv_proxy"]), 4),
            "cluster": int(row["cluster"]),
        })

    return {
        "clusters": cluster_points,
        "summary": cluster_summaries,
        "n_clusters": n_clusters,
    }


def generate_insights(df: pd.DataFrame, anomalies: list, skew_data: list,
                      smile_data: list, spike_data: list, cluster_data: dict) -> dict:
    """
    Generate a structured insight summary from all analytics.
    """
    # Determine dominant pattern
    dominant_patterns = []
    for s in skew_data:
        if s["pattern"] != "Neutral":
            dominant_patterns.append(s["pattern"])
    for sm in smile_data:
        if sm["has_smile"]:
            dominant_patterns.append("Volatility Smile")

    # Find hotspot strikes from clusters
    hotspot_strikes = []
    if cluster_data.get("summary"):
        for cs in cluster_data["summary"]:
            if "High" in cs["activity_level"]:
                hotspot_strikes.extend([cs["strike_range"][0], cs["strike_range"][1]])

    # PCR trend
    latest_pcr_data = df.groupby("datetime").agg(
        total_ce=("oi_CE", "sum"),
        total_pe=("oi_PE", "sum"),
    ).reset_index().sort_values("datetime")

    if len(latest_pcr_data) > 1:
        latest_pcr_data["pcr"] = latest_pcr_data["total_pe"] / latest_pcr_data["total_ce"].replace(0, 1)
        recent_pcr = latest_pcr_data["pcr"].tail(5).mean()
        older_pcr = latest_pcr_data["pcr"].head(5).mean()

        if recent_pcr > older_pcr * 1.1:
            pcr_trend = "Increasing (Put Buying → Bearish Sentiment)"
        elif recent_pcr < older_pcr * 0.9:
            pcr_trend = "Decreasing (Call Buying → Bullish Sentiment)"
        else:
            pcr_trend = "Stable"

        current_pcr = round(float(recent_pcr), 4)
    else:
        pcr_trend = "Insufficient data"
        current_pcr = None

    # Market sentiment
    bearish_signals = sum(1 for p in dominant_patterns if "Bearish" in p or "Fear" in p)
    bullish_signals = sum(1 for p in dominant_patterns if "Bullish" in p)

    if bearish_signals > bullish_signals:
        sentiment = "Bearish / Cautious"
    elif bullish_signals > bearish_signals:
        sentiment = "Bullish / Optimistic"
    else:
        sentiment = "Neutral / Mixed"

    return {
        "total_data_points": int(len(df)),
        "date_range": {
            "start": str(df["datetime"].min()),
            "end": str(df["datetime"].max()),
        },
        "expiries_analyzed": sorted([str(e)[:10] for e in df["expiry"].dropna().unique()]),
        "anomaly_count": len(anomalies),
        "dominant_patterns": dominant_patterns if dominant_patterns else ["No strong patterns detected"],
        "hotspot_strikes": sorted(set(hotspot_strikes)),
        "iv_spike_count": len(spike_data),
        "iv_spike_timestamps": [s["datetime"] for s in spike_data[:10]],
        "market_sentiment": sentiment,
        "pcr_trend": pcr_trend,
        "current_pcr": current_pcr,
        "smile_detected": bool(any(sm["has_smile"] for sm in smile_data)),
        "cluster_count": cluster_data.get("n_clusters", 0),
    }
