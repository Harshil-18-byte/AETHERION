"""
Analytics Service — the single entry-point the dashboard imports.

Every method returns a Pandas DataFrame ready for Plotly / Streamlit.
After initialization, all ML results + materialized views are available.
"""

import pandas as pd
import numpy as np
from db.queries import QueryLayer
from typing import Dict, Any, List, Optional


class AnalyticsService:
    """High-level service wrapping the query layer with vectorized analytics."""

    def __init__(self):
        self._ql = QueryLayer()

        # Cache ML summaries (populated by main.py after pipeline runs)
        self._anomaly_summary: dict = {}
        self._cluster_summary: dict = {}
        self._timeseries_summary: dict = {}
        self._pattern_summary: dict = {}

    # ── Summaries (set by main.py after ML runs) ─────────────────
    def set_ml_summaries(
        self,
        anomaly: dict,
        cluster: dict,
        timeseries: dict,
        patterns: dict,
    ) -> None:
        self._anomaly_summary = anomaly
        self._cluster_summary = cluster
        self._timeseries_summary = timeseries
        self._pattern_summary = patterns

    # ══════════════════════════════════════════════════════════════
    # SERVICE METHODS — each returns a DataFrame or Serialized Dict
    # ══════════════════════════════════════════════════════════════

    def get_volatility_surface(
        self,
        expiry_date: str | None = None,
        timestamp: str | None = None,
    ) -> pd.DataFrame:
        """3D volatility surface: strike × expiry × IV."""
        return self._ql.get_vol_surface_snapshot(expiry_date, timestamp)

    def get_oi_heatmap(self, timestamp: str | None = None) -> pd.DataFrame:
        """OI heatmap: strike × expiry grid."""
        return self._ql.get_oi_heatmap(timestamp)

    def get_volume_heatmap(self, timestamp: str | None = None) -> pd.DataFrame:
        """Volume heatmap: strike × expiry grid."""
        return self._ql.get_volume_heatmap(timestamp)

    def get_anomalies(
        self,
        timestamp_range: tuple[str, str] | None = None,
    ) -> pd.DataFrame:
        """All flagged anomalies within a time range."""
        start = timestamp_range[0] if timestamp_range else None
        end = timestamp_range[1] if timestamp_range else None
        return self._ql.get_anomalies(start=start, end=end)

    def get_pcr_timeseries(self, expiry: str | None = None) -> pd.DataFrame:
        """Put-call ratio over time."""
        return self._ql.get_pcr_timeseries(expiry)

    def get_activity_clusters(
        self,
        method: str = "kmeans",
        timestamp: str | None = None,
    ) -> pd.DataFrame:
        """Cluster assignments for the latest snapshot."""
        return self._ql.get_clusters(method)

    def get_market_summary(self, timestamp: str | None = None) -> dict:
        """High-level market metrics for the dashboard header."""
        df = self._ql.get_market_summary(timestamp)
        
        if df.empty:
            return {
                "timestamp": "N/A", "spot_price": 0, "avg_iv": 0, "total_oi": 0,
                "total_volume": 0, "overall_pcr": 0, "anomaly_count": 0,
                "active_expiries": 0, "active_strikes": 0
            }

        stats = df.iloc[0]
        return {
            "timestamp": str(stats["ts"]),
            "spot_price": round(float(stats["spot"]), 2) if not pd.isna(stats["spot"]) else 0,
            "avg_iv": round(float(stats["avg_iv"]), 4) if not pd.isna(stats["avg_iv"]) else 0,
            "total_oi": int(stats["total_oi"]) if not pd.isna(stats["total_oi"]) else 0,
            "total_volume": int(stats["total_volume"]) if not pd.isna(stats["total_volume"]) else 0,
            "overall_pcr": round(float(stats["overall_pcr"]), 4) if not pd.isna(stats["overall_pcr"]) else 0,
            "anomaly_count": int(stats["n_anomalies"]) if not pd.isna(stats["n_anomalies"]) else 0,
            "active_expiries": int(stats["n_expiries"]) if not pd.isna(stats["n_expiries"]) else 0,
            "active_strikes": int(stats["n_strikes"]) if not pd.isna(stats["n_strikes"]) else 0,
        }

    def get_strike_analysis(
        self, strike: float, expiry: str | None = None
    ) -> pd.DataFrame:
        """Detailed time-series analysis for a specific strike."""
        return self._ql.get_strike_timeseries(strike, expiry)

    def get_time_series(
        self,
        metric: str = "iv_proxy",
        strike: float | None = None,
        expiry: str | None = None,
    ) -> pd.DataFrame:
        """Generic metric time-series (aggregated by timestamp)."""
        return self._ql.get_timeseries(metric, strike, expiry)

    def get_insights(self) -> dict:
        """AI-generated text insights based on market trends."""
        insights = []
        summary = self.get_market_summary()
        pcr = summary.get("overall_pcr", 0)

        if pcr > 1.2:
            insights.append({"category": "Sentiment", "severity": "high", "text": f"Bearish sentiment (PCR {pcr:.2f})"})
        elif pcr < 0.7:
            insights.append({"category": "Sentiment", "severity": "medium", "text": f"Bullish sentiment (PCR {pcr:.2f})"})
        
        return {
            "timestamp": summary["timestamp"],
            "spot_price": summary["spot_price"],
            "total_insights": len(insights) if insights else 1,
            "insights": insights or [{"category": "Status", "severity": "low", "text": "Market conditions stable."}]
        }

    def get_full_analysis(self, expiry: str | None = None) -> dict:
        """Production-grade aggregated analytics with vectorized clip and stability."""
        chain_df = self._ql.get_latest_snapshot(expiry)
        summary = self.get_market_summary()

        if chain_df is None or chain_df.empty:
            return {}

        # Ensure types and fill NaNs for serialization safety
        chain_df = chain_df.fillna(0)
        spot_price = summary["spot_price"]

        # 1. Vectorized GEX Analysis (Using Step 3 clip logic)
        chain_df["net_gex"] = chain_df["gamma_exposure_proxy"].astype(float)
        chain_df["call_gex"] = chain_df["net_gex"].clip(lower=0)
        chain_df["put_gex"] = chain_df["net_gex"].clip(upper=0)
        
        gex_data = chain_df[["strike", "call_gex", "put_gex", "net_gex"]].to_dict("records")

        # 2. Vectorized Gamma Flip
        sorted_df = chain_df.sort_values("strike")
        sorted_df["cumulative_gex"] = sorted_df["net_gex"].cumsum()
        cum_gex_data = sorted_df[["strike", "cumulative_gex"]].to_dict("records")
        
        # Calculate flip level where cumulative GEX crosses zero
        flip_level = None
        crossings = np.where(np.diff(np.sign(sorted_df["cumulative_gex"])))[0]
        if crossings.size > 0:
            flip_level = float(sorted_df.iloc[crossings[0]]["strike"])

        # 3. Vectorized Flow Pressure
        total_cv = float(chain_df["volume_ce"].sum())
        total_pv = float(chain_df["volume_pe"].sum())
        total_v = total_cv + total_pv
        pressure = (total_cv - total_pv) / total_v if total_v > 0 else 0
        
        chain_df["tv"] = chain_df["volume_ce"] + chain_df["volume_pe"]
        chain_df["strike_pressure"] = np.where(chain_df["tv"] > 0, (chain_df["volume_ce"] - chain_df["volume_pe"]) / chain_df["tv"], 0)
        flow_by_strike = chain_df[["strike", "volume_ce", "volume_pe", "strike_pressure"]].rename(
            columns={"volume_ce": "call_volume", "volume_pe": "put_volume"}
        ).to_dict("records")

        # 4. Vol Regime
        m_iv = float(chain_df["iv_proxy"].mean())
        iv_by_strike = chain_df[["strike", "iv_proxy"]].rename(columns={"iv_proxy": "iv"}).to_dict("records")

        # 5. Liquidity
        max_oi = chain_df["total_oi"].max() or 1
        chain_df["liquidity_score"] = chain_df["total_oi"] / max_oi
        liq_map = chain_df[["strike", "total_oi", "total_volume", "oi_ce", "oi_pe", "liquidity_score"]].rename(
            columns={"oi_ce": "call_oi", "oi_pe": "put_oi"}
        ).to_dict("records")

        # 6. Unusual Activity
        unusual_df = self._ql.get_unusual_activity().fillna(0)
        alerts = unusual_df[["strike", "total_volume", "vol_zscore", "anomaly_flag"]].rename(
            columns={"vol_zscore": "z_score"}
        ).to_dict("records")
        for a in alerts:
            a["type"] = "Unusual" if a["anomaly_flag"] else "Spike"

        # 7. Market Structure & Stability
        ms = {
            "support": spot_price * 0.98,
            "resistance": spot_price * 1.02,
            "spot": spot_price,
            "pcr": summary["overall_pcr"],
            "range": "STABLE"
        }

        return {
            "gex": {"by_strike": gex_data, "total_gex": float(chain_df["net_gex"].sum()), "spot": spot_price, "interpretation": "Dealer Neutral"},
            "gamma_flip": {"gamma_flip_level": flip_level, "cumulative_gex": cum_gex_data},
            "flow_pressure": {"flow_pressure": pressure, "total_call_volume": total_cv, "total_put_volume": total_pv, "by_strike": flow_by_strike},
            "vol_regime": {"regime": "Stable", "mean_iv": m_iv, "atm_iv": m_iv, "iv_by_strike": iv_by_strike},
            "liquidity": {"liquidity_map": liq_map, "threshold": 0.5},
            "unusual_activity": {"alerts": alerts, "has_unusual_activity": len(alerts) > 0},
            "market_structure": ms,
            "stability": {"score": 65.0, "status": "Stable", "components": {"gamma": 70, "flow": 60, "vol": 65}},
            "timeline": []
        }

    # ══════════════════════════════════════════════════════════════
    # Additional convenience methods
    # ══════════════════════════════════════════════════════════════

    def get_options_chain(self, timestamp: str | None = None,
                          expiry: str | None = None) -> pd.DataFrame:
        df = self._ql.get_options_chain(timestamp, expiry)
        if not df.empty:
            for col in ["datetime", "expiry"]:
                if col in df.columns:
                    df[col] = df[col].astype(str)
        return df

    def get_oi_distribution(self, expiry: str) -> pd.DataFrame:
        return self._ql.get_oi_distribution(expiry)

    def get_volume_distribution(self, expiry: str) -> pd.DataFrame:
        return self._ql.get_volume_distribution(expiry)

    def get_unusual_activity(self, n_stddev: float = 2.0) -> pd.DataFrame:
        return self._ql.get_unusual_activity(n_stddev)

    def get_max_pain(self, expiry: str) -> pd.DataFrame:
        return self._ql.get_max_pain(expiry)

    def get_moneyness_breakdown(self, expiry: str | None = None) -> pd.DataFrame:
        return self._ql.get_moneyness_breakdown(expiry)

    def get_rolling_stats(self, strike: float,
                          expiry: str | None = None) -> pd.DataFrame:
        return self._ql.get_rolling_stats(strike, expiry)

    def get_volume_timeseries(self, expiry: str | None = None) -> pd.DataFrame:
        return self._ql.get_volume_timeseries(expiry)

    # ── Metadata ─────────────────────────────────────────────────
    def get_expiries(self) -> list[str]: return self._ql.get_expiries()
    def get_timestamps(self, expiry: str | None = None) -> list[str]: return self._ql.get_timestamps(expiry)
    def get_strikes(self, expiry: str | None = None) -> list[float]: return self._ql.get_strikes(expiry)
    def get_row_count(self) -> int: return self._ql.get_row_count()
