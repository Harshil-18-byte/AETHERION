"""
Query Layer — reusable DuckDB SQL functions returning Pandas DataFrames.

Every public method runs a parameterized SQL query and returns a DataFrame
that is ready for Plotly / Streamlit consumption.
"""

import pandas as pd
from db.connection import get_connection


class QueryLayer:
    """Stateless query executor bound to the shared SQLite connection."""

    def __init__(self):
        self.conn = get_connection()

    def _q(self, sql: str, params: list | None = None) -> pd.DataFrame:
        """Execute SQL and return DataFrame."""
        return self.conn.execute(sql, params).df()

    def get_options_chain(self, timestamp: str | None = None,
                          expiry: str | None = None) -> pd.DataFrame:
        """Full chain at a given timestamp (or latest)."""
        where = []
        params = []
        if expiry:
            where.append("expiry = ?")
            params.append(expiry)
        if timestamp:
            where.append("datetime = ?")
            params.append(timestamp)
        else:
            subq = "datetime = (SELECT MAX(datetime) FROM options_enriched"
            if expiry:
                subq += " WHERE expiry = ?"
                params.append(expiry)
            subq += ")"
            where.append(subq)

        clause = " AND ".join(where) if where else "1=1"
        sql = f"""
            SELECT symbol, strike, expiry, CE, PE, spot_close, ATM,
                   oi_CE, oi_PE, volume_CE, volume_PE,
                   total_oi, total_volume,
                   iv_proxy, pcr_oi, pcr_volume, moneyness,
                   days_to_expiry, anomaly_flag, cluster_kmeans,
                   unusual_activity_score, datetime
            FROM options_enriched
            WHERE {clause}
            ORDER BY strike
        """
        return self._q(sql, params)

    def get_strike_timeseries(self, strike: float,
                              expiry: str | None = None) -> pd.DataFrame:
        where = "strike = ?"
        params: list = [strike]
        if expiry:
            where += " AND expiry = ?"
            params.append(expiry)
        sql = f"""
            SELECT datetime, CE, PE, iv_proxy, oi_CE, oi_PE,
                   volume_CE, volume_PE, total_oi, total_volume,
                   pcr_oi, spot_close, anomaly_flag
            FROM options_enriched
            WHERE {where}
            ORDER BY datetime
        """
        return self._q(sql, params)

    def get_volatility_surface(self, expiry: str | None = None) -> pd.DataFrame:
        if expiry:
            return self._q(
                "SELECT * FROM mv_volatility_surface WHERE expiry = ?",
                [expiry],
            )
        return self._q("SELECT * FROM mv_volatility_surface")

    def get_oi_heatmap(self, timestamp: str | None = None) -> pd.DataFrame:
        if timestamp:
            return self._q("""
                SELECT strike, expiry, oi_CE, oi_PE, total_oi
                FROM options_enriched
                WHERE datetime = ?
                ORDER BY expiry, strike
            """, [timestamp])
        return self._q("SELECT * FROM mv_oi_distribution ORDER BY expiry, strike")

    def get_volume_heatmap(self, timestamp: str | None = None) -> pd.DataFrame:
        if timestamp:
            return self._q("""
                SELECT strike, expiry, volume_CE, volume_PE, total_volume
                FROM options_enriched
                WHERE datetime = ?
                ORDER BY expiry, strike
            """, [timestamp])
        return self._q("""
            WITH latest AS (
                SELECT expiry, MAX(datetime) AS max_dt
                FROM options_enriched GROUP BY expiry
            )
            SELECT e.strike, e.expiry, e.volume_CE, e.volume_PE, e.total_volume
            FROM options_enriched e
            JOIN latest l ON e.expiry = l.expiry AND e.datetime = l.max_dt
            ORDER BY e.expiry, e.strike
        """)

    def get_oi_distribution(self, expiry: str) -> pd.DataFrame:
        return self._q("""
            SELECT strike, oi_CE, oi_PE, total_oi, pcr_oi
            FROM mv_oi_distribution
            WHERE expiry = ?
            ORDER BY strike
        """, [expiry])

    def get_volume_distribution(self, expiry: str) -> pd.DataFrame:
        return self._q("""
            SELECT strike, volume_CE, volume_PE,
                   volume_CE + volume_PE AS total_volume
            FROM mv_pcr_by_strike
            WHERE expiry = ?
            ORDER BY strike
        """, [expiry])

    def get_unusual_activity(self, n_stddev: float = 2.0,
                             limit: int = 100) -> pd.DataFrame:
        # Simplified unusual activity for SQLite (using simple average volume spikes)
        return self._q(f"""
            WITH stats AS (
                SELECT AVG(total_volume) AS mu
                FROM options_enriched
            )
            SELECT e.datetime, e.strike, e.expiry, e.total_volume,
                   e.iv_proxy, e.anomaly_flag, e.unusual_activity_score,
                   e.spot_close, e.moneyness,
                   e.total_volume / NULLIF(s.mu, 0) AS vol_zscore
            FROM options_enriched e, stats s
            WHERE e.total_volume / NULLIF(s.mu, 0) > {n_stddev}
            ORDER BY vol_zscore DESC
            LIMIT {limit}
        """)

    def get_pcr_timeseries(self, expiry: str | None = None) -> pd.DataFrame:
        where = f"WHERE expiry = '{expiry}'" if expiry else ""
        return self._q(f"""
            SELECT datetime,
                   CAST(SUM(oi_PE) AS DOUBLE) / NULLIF(SUM(oi_CE), 0) AS pcr_oi,
                   CAST(SUM(volume_PE) AS DOUBLE) / NULLIF(SUM(volume_CE), 0) AS pcr_volume,
                   SUM(total_oi) AS total_oi,
                   SUM(total_volume) AS total_volume,
                   AVG(spot_close) AS spot_close
            FROM options_enriched
            {where}
            GROUP BY datetime
            ORDER BY datetime
        """)

    def get_max_pain(self, expiry: str) -> pd.DataFrame:
        return self._q("""
            SELECT settlement_price, call_liability, put_liability, total_liability
            FROM mv_max_pain
            WHERE expiry = ?
            ORDER BY total_liability ASC
        """, [expiry])

    def get_moneyness_breakdown(self, expiry: str | None = None) -> pd.DataFrame:
        where = f"AND expiry = '{expiry}'" if expiry else ""
        return self._q(f"""
            WITH latest AS (
                SELECT MAX(datetime) AS max_dt FROM options_enriched
            ),
            classified AS (
                SELECT
                    *,
                    CASE
                        WHEN ABS(moneyness - 1.0) < 0.01 THEN 'ATM'
                        WHEN moneyness < 1.0 THEN 'ITM_CE / OTM_PE'
                        ELSE 'OTM_CE / ITM_PE'
                    END AS money_class
                FROM options_enriched
                WHERE datetime = (SELECT max_dt FROM latest)
                  {where}
            )
            SELECT money_class,
                   COUNT(*) AS n_strikes,
                   SUM(oi_CE) AS total_oi_CE,
                   SUM(oi_PE) AS total_oi_PE,
                   SUM(volume_CE) AS total_vol_CE,
                   SUM(volume_PE) AS total_vol_PE,
                   AVG(iv_proxy) AS avg_iv
            FROM classified
            GROUP BY money_class
        """)

    def get_rolling_stats(self, strike: float,
                          expiry: str | None = None) -> pd.DataFrame:
        where = "WHERE strike = ?"
        params: list = [strike]
        if expiry:
            where += " AND expiry = ?"
            params.append(expiry)
        return self._q(f"""
            SELECT datetime, iv_proxy, total_oi, total_volume,
                   iv_ma5, iv_ma10, iv_ma20, iv_std20,
                   oi_ma5, vol_ma5, spot_close
            FROM mv_rolling_stats
            {where}
            ORDER BY datetime
        """, params)

    def get_anomalies(self, start: str | None = None,
                      end: str | None = None,
                      limit: int = 200) -> pd.DataFrame:
        where_parts = ["anomaly_flag = 1"]
        params = []
        if start:
            where_parts.append("datetime >= ?")
            params.append(start)
        if end:
            where_parts.append("datetime <= ?")
            params.append(end)
        clause = " AND ".join(where_parts)
        return self._q(f"""
            SELECT datetime, strike, expiry, iv_proxy,
                   total_volume, total_oi, anomaly_score,
                   unusual_activity_score, spot_close, moneyness,
                   cluster_kmeans
            FROM options_enriched
            WHERE {clause}
            ORDER BY anomaly_score ASC
            LIMIT {limit}
        """, params)

    def get_clusters(self, method: str = "kmeans") -> pd.DataFrame:
        col = "cluster_kmeans" if method == "kmeans" else "cluster_dbscan"
        return self._q(f"""
            WITH latest AS (
                SELECT expiry, MAX(datetime) AS max_dt
                FROM options_enriched GROUP BY expiry
            )
            SELECT e.strike, e.expiry, e.total_volume, e.total_oi,
                   e.iv_proxy, e.moneyness, e.{col} AS cluster
            FROM options_enriched e
            JOIN latest l ON e.expiry = l.expiry AND e.datetime = l.max_dt
            ORDER BY e.{col}, e.strike
        """)

    def get_expiries(self) -> list[str]:
        df = self._q("SELECT DISTINCT expiry FROM options_enriched ORDER BY expiry")
        return [str(e)[:10] for e in df["expiry"].tolist()]

    def get_timestamps(self, expiry: str | None = None) -> list[str]:
        where = f"WHERE expiry = '{expiry}'" if expiry else ""
        df = self._q(f"SELECT DISTINCT datetime FROM options_enriched {where} ORDER BY datetime")
        return [str(t) for t in df["datetime"].tolist()]

    def get_strikes(self, expiry: str | None = None) -> list[float]:
        where = f"WHERE expiry = '{expiry}'" if expiry else ""
        df = self._q(f"SELECT DISTINCT strike FROM options_enriched {where} ORDER BY strike")
        return df["strike"].tolist()

    def get_row_count(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM options_enriched").fetchone()[0]

    def get_volume_timeseries(self, expiry: str | None = None) -> pd.DataFrame:
        if expiry:
            return self._q(
                "SELECT * FROM mv_volume_timeseries WHERE expiry = ? ORDER BY bucket",
                [expiry],
            )
        return self._q("SELECT * FROM mv_volume_timeseries ORDER BY bucket")

    def get_timeseries(self, metric: str = "iv_proxy",
                       strike: float | None = None,
                       expiry: str | None = None) -> pd.DataFrame:
        allowed = {"iv_proxy", "total_oi", "total_volume", "pcr_oi",
                    "pcr_volume", "spot_close", "CE", "PE", "moneyness",
                    "relative_volume", "gamma_exposure_proxy", "cum_delta_proxy"}
        if metric not in allowed:
            raise ValueError(f"Metric '{metric}' not allowed. Use one of {allowed}")
        where_parts = []
        params = []
        if strike:
            where_parts.append("strike = ?")
            params.append(strike)
        if expiry:
            where_parts.append("expiry = ?")
            params.append(expiry)
        clause = " AND ".join(where_parts) if where_parts else "1=1"
        return self._q(f"""
            SELECT datetime, AVG({metric}) AS {metric}, AVG(spot_close) AS spot_close
            FROM options_enriched
            WHERE {clause}
            GROUP BY datetime
            ORDER BY datetime
        """, params)
