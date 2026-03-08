"""
Analytics Service — the single entry-point the dashboard imports.

Every method returns a Pandas DataFrame ready for Plotly / Streamlit.
After initialization, all ML results + materialized views are available.

Usage:
    from services import AnalyticsService
    svc = AnalyticsService()
    df = svc.get_volatility_surface("2026-02-17")
"""

import pandas as pd
from db.queries import QueryLayer


class AnalyticsService:
    """High-level service wrapping the query layer with caching references."""

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
    # SERVICE METHODS — each returns a DataFrame
    # ══════════════════════════════════════════════════════════════

    def get_volatility_surface(
        self,
        expiry_date: str | None = None,
        timestamp: str | None = None,
    ) -> pd.DataFrame:
        """3D volatility surface: strike × expiry × IV."""
        if timestamp:
            from db.connection import get_connection
            conn = get_connection()
            return conn.execute("""
                SELECT strike, expiry, iv_proxy AS avg_iv, moneyness
                FROM options_enriched
                WHERE datetime = ?::TIMESTAMP
                ORDER BY expiry, strike
            """, [timestamp]).df()
        return self._ql.get_volatility_surface(expiry_date)

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
        from db.connection import get_connection
        conn = get_connection()

        if timestamp:
            where = f"WHERE datetime = '{timestamp}'::TIMESTAMP"
        else:
            where = "WHERE datetime = (SELECT MAX(datetime) FROM options_enriched)"

        stats = conn.execute(f"""
            SELECT
                AVG(spot_close)     AS spot,
                AVG(iv_proxy)       AS avg_iv,
                SUM(total_oi)       AS total_oi,
                SUM(total_volume)   AS total_volume,
                SUM(oi_PE)::DOUBLE / NULLIF(SUM(oi_CE), 0) AS overall_pcr,
                SUM(CASE WHEN anomaly_flag = 1 THEN 1 ELSE 0 END) AS n_anomalies,
                COUNT(DISTINCT expiry)  AS n_expiries,
                COUNT(DISTINCT strike)  AS n_strikes,
                MIN(datetime) AS ts
            FROM options_enriched
            {where}
        """).fetchone()

        return {
            "timestamp": str(stats[8]),
            "spot_price": round(float(stats[0]), 2) if stats[0] else 0,
            "avg_iv": round(float(stats[1]), 4) if stats[1] else 0,
            "total_oi": int(stats[2]) if stats[2] else 0,
            "total_volume": int(stats[3]) if stats[3] else 0,
            "overall_pcr": round(float(stats[4]), 4) if stats[4] else 0,
            "anomaly_count": int(stats[5]) if stats[5] else 0,
            "active_expiries": int(stats[6]) if stats[6] else 0,
            "active_strikes": int(stats[7]) if stats[7] else 0,
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
        """
        AI-generated text insights — combines ML summaries
        into a structured report for the dashboard.
        """
        insights = []

        # ── PCR insight ──────────────────────────────────────────
        summary = self.get_market_summary()
        pcr = summary.get("overall_pcr", 0)
        if pcr > 1.2:
            insights.append({
                "category": "Sentiment",
                "severity": "high",
                "text": f"Strong bearish sentiment — overall PCR is {pcr:.2f} "
                        f"(above 1.2 threshold). Put writers dominate.",
            })
        elif pcr < 0.7:
            insights.append({
                "category": "Sentiment",
                "severity": "medium",
                "text": f"Bullish sentiment — overall PCR is {pcr:.2f} "
                        f"(below 0.7). Call buying dominates.",
            })
        else:
            insights.append({
                "category": "Sentiment",
                "severity": "low",
                "text": f"Neutral sentiment — PCR at {pcr:.2f}.",
            })

        # ── Anomaly insight ──────────────────────────────────────
        n_anom = summary.get("anomaly_count", 0)
        if n_anom > 50:
            insights.append({
                "category": "Anomalies",
                "severity": "high",
                "text": f"{n_anom} anomalous data points detected at current timestamp. "
                        f"Unusual market activity — investigate volume spikes.",
            })

        # ── IV Trends ────────────────────────────────────────────
        for tr in self._timeseries_summary.get("iv_trends", []):
            if tr["direction"] == "RISING":
                insights.append({
                    "category": "Volatility",
                    "severity": "medium",
                    "text": f"IV is RISING for {tr['expiry']} expiry "
                            f"(slope={tr['slope']:.4f}, R²={tr['r2']:.2f}). "
                            f"Possible event anticipation.",
                })
            elif tr["direction"] == "FALLING":
                insights.append({
                    "category": "Volatility",
                    "severity": "low",
                    "text": f"IV is DECLINING for {tr['expiry']} expiry. "
                            f"Volatility crush may be underway.",
                })

        # ── OI Trends ────────────────────────────────────────────
        for tr in self._timeseries_summary.get("oi_trends", []):
            if tr["direction"] == "BUILDUP":
                insights.append({
                    "category": "Open Interest",
                    "severity": "medium",
                    "text": f"OI BUILDUP for {tr['expiry']} expiry "
                            f"({tr['oi_change_pct']:+.1f}%). Fresh positions being added.",
                })
            elif tr["direction"] == "UNWINDING":
                insights.append({
                    "category": "Open Interest",
                    "severity": "medium",
                    "text": f"OI UNWINDING for {tr['expiry']} expiry "
                            f"({tr['oi_change_pct']:+.1f}%). Positions being closed.",
                })

        # ── Smile/Skew ───────────────────────────────────────────
        for pat in self._pattern_summary.get("smile_skew", []):
            if pat["pattern"] not in ("FLAT",):
                insights.append({
                    "category": "Vol Pattern",
                    "severity": "medium",
                    "text": f"{pat['pattern']} detected for {pat['expiry']}. "
                            f"Put skew: {pat['put_skew_pct']:+.1f}%, "
                            f"Call skew: {pat['call_skew_pct']:+.1f}%.",
                })

        # ── Support/Resistance ───────────────────────────────────
        for sr in self._pattern_summary.get("support_resistance", []):
            supports = [s["strike"] for s in sr.get("support_levels", [])]
            resistances = [r["strike"] for r in sr.get("resistance_levels", [])]
            if supports or resistances:
                insights.append({
                    "category": "Levels",
                    "severity": "low",
                    "text": f"{sr['expiry']}: Support at {supports}, "
                            f"Resistance at {resistances} "
                            f"(spot: {sr['spot']}).",
                })

        # ── Max Pain ─────────────────────────────────────────────
        for mp in self._pattern_summary.get("max_pain", []):
            insights.append({
                "category": "Max Pain",
                "severity": "low",
                "text": f"Max pain for {mp['expiry']}: {mp['max_pain_strike']:,.0f}.",
            })

        # ── Volume Buildups ──────────────────────────────────────
        for vb in self._timeseries_summary.get("volume_buildups", []):
            if vb["signal"] in ("STRONG_BUILDUP", "MODERATE_BUILDUP"):
                insights.append({
                    "category": "Volume",
                    "severity": "medium",
                    "text": f"{vb['signal']} detected for {vb['expiry']} — "
                            f"recent volume {vb['recent_vs_avg_ratio']:.1f}x average.",
                })

        return {
            "timestamp": summary["timestamp"],
            "spot_price": summary["spot_price"],
            "total_insights": len(insights),
            "insights": insights,
        }

    # ══════════════════════════════════════════════════════════════
    # Additional convenience methods
    # ══════════════════════════════════════════════════════════════

    def get_options_chain(self, timestamp: str | None = None,
                          expiry: str | None = None) -> pd.DataFrame:
        df = self._ql.get_options_chain(timestamp, expiry)
        if not df.empty:
            if "datetime" in df.columns:
                df["datetime"] = df["datetime"].astype(str)
            if "expiry" in df.columns:
                df["expiry"] = df["expiry"].astype(str)
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
    def get_expiries(self) -> list[str]:
        return self._ql.get_expiries()

    def get_timestamps(self, expiry: str | None = None) -> list[str]:
        return self._ql.get_timestamps(expiry)

    def get_strikes(self, expiry: str | None = None) -> list[float]:
        return self._ql.get_strikes(expiry)

    def get_row_count(self) -> int:
        return self._ql.get_row_count()

    # ── ML Summaries ─────────────────────────────────────────────
    def get_anomaly_summary(self) -> dict:
        return self._anomaly_summary

    def get_cluster_summary(self) -> dict:
        return self._cluster_summary

    def get_trend_summary(self) -> dict:
        return self._timeseries_summary

    def get_pattern_summary(self) -> dict:
        return self._pattern_summary
