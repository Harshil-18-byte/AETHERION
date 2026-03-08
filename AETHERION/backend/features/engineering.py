"""
Feature Engineering — computed columns added via SQL transformations.

All features are computed inside DuckDB using window functions and
SQL expressions, then written to options_enriched.
"""

from db.connection import get_connection
from features.pricing import calculate_greeks


def run_feature_engineering() -> int:
    """
    Read from options_raw, compute all features, and INSERT into options_enriched.
    Returns the number of enriched rows.
    """
    conn = get_connection()

    # Clear enriched table for a clean re-computation
    conn.execute("DELETE FROM options_enriched")

    # ────────────────────────────────────────────────────────────
    # Single SQL that computes ALL engineered features.
    # Uses CTEs and window functions for lag-based changes.
    # ────────────────────────────────────────────────────────────
    conn.execute("""
        CREATE TEMP TABLE tmp_enriched AS
        WITH base AS (
            SELECT
                *,
                -- aggregated totals
                COALESCE(oi_CE, 0) + COALESCE(oi_PE, 0)         AS total_oi,
                COALESCE(volume_CE, 0) + COALESCE(volume_PE, 0) AS total_volume,

                -- (a) Moneyness: strike / spot
                CASE WHEN spot_close > 0
                     THEN strike / spot_close
                     ELSE NULL END                                AS moneyness,

                -- (b) Days to expiry
                CASE WHEN expiry IS NOT NULL AND datetime IS NOT NULL
                     THEN DATE_DIFF('day', CAST(datetime AS DATE), expiry)
                     ELSE NULL END                                AS days_to_expiry,

                -- (c) Put-call OI ratio
                CASE WHEN oi_CE > 0
                     THEN CAST(oi_PE AS DOUBLE) / oi_CE
                     ELSE NULL END                                AS pcr_oi,

                -- (d) Put-call volume ratio
                CASE WHEN volume_CE > 0
                     THEN CAST(volume_PE AS DOUBLE) / volume_CE
                     ELSE NULL END                                AS pcr_volume,

                -- (g) IV proxy: intrinsic + extrinsic value ratio
                CASE WHEN spot_close > 0
                     THEN (COALESCE(CE, 0) + COALESCE(PE, 0)) / spot_close * 100.0
                     ELSE 0 END                                   AS iv_proxy

            FROM options_raw
        ),
        with_lags AS (
            SELECT
                b.*,

                -- OI changes vs previous timestamp (same strike + expiry)
                b.oi_CE - LAG(b.oi_CE) OVER w_se                 AS oi_change_CE,
                b.oi_PE - LAG(b.oi_PE) OVER w_se                 AS oi_change_PE,

                -- (e) Volume % change
                CASE WHEN LAG(b.total_volume) OVER w_se > 0
                     THEN (b.total_volume - LAG(b.total_volume) OVER w_se)
                           / LAG(b.total_volume) OVER w_se * 100.0
                     ELSE 0 END                                   AS volume_change_pct,

                -- (f) OI % change
                CASE WHEN LAG(b.total_oi) OVER w_se > 0
                     THEN (b.total_oi - LAG(b.total_oi) OVER w_se)
                           / LAG(b.total_oi) OVER w_se * 100.0
                     ELSE 0 END                                   AS oi_change_pct,

                -- (g) Relative volume = current / rolling avg(20)
                CASE WHEN AVG(b.total_volume) OVER w20_se > 0
                     THEN b.total_volume / AVG(b.total_volume) OVER w20_se
                     ELSE 1.0 END                                 AS relative_volume,

                -- (h) IV rank = (current - min) / (max - min) over rolling 50
                CASE WHEN MAX(b.iv_proxy) OVER w50_se - MIN(b.iv_proxy) OVER w50_se > 0
                     THEN (b.iv_proxy - MIN(b.iv_proxy) OVER w50_se)
                         / (MAX(b.iv_proxy) OVER w50_se - MIN(b.iv_proxy) OVER w50_se)
                     ELSE 0.5 END                                 AS iv_rank,

                -- IV percentile = PERCENT_RANK over rolling 50
                PERCENT_RANK() OVER w50_se                        AS iv_percentile,

                -- (i) Gamma exposure proxy
                --     Rough proxy: OI * spot^2 * 0.01 * (1 / DTE_factor)
                CASE WHEN b.days_to_expiry > 0
                     THEN (b.total_oi * b.spot_close * 0.0001)
                         / SQRT(CAST(b.days_to_expiry AS DOUBLE))
                     ELSE 0 END                                   AS gamma_exposure_proxy,

                -- (j) Cumulative delta approximation
                --     Positive for ITM calls, negative for ITM puts
                CASE
                    WHEN b.moneyness < 0.97 THEN  b.oi_CE * 0.8   -- deep ITM CE
                    WHEN b.moneyness < 1.0  THEN  b.oi_CE * 0.5   -- slightly ITM CE
                    WHEN b.moneyness < 1.03 THEN -b.oi_PE * 0.5   -- slightly ITM PE
                    ELSE                         -b.oi_PE * 0.8    -- deep ITM PE
                END                                               AS cum_delta_proxy

            FROM base b
            WINDOW
                w_se     AS (PARTITION BY b.strike, b.expiry ORDER BY b.datetime),
                w20_se   AS (PARTITION BY b.strike, b.expiry ORDER BY b.datetime
                             ROWS BETWEEN 19 PRECEDING AND CURRENT ROW),
                w50_se   AS (PARTITION BY b.strike, b.expiry ORDER BY b.datetime
                             ROWS BETWEEN 49 PRECEDING AND CURRENT ROW)
        )
        SELECT
            symbol, datetime, expiry, CE, PE, spot_close, ATM, strike,
            oi_CE, oi_PE, volume_CE, volume_PE,
            total_oi, total_volume,
            moneyness, days_to_expiry,
            pcr_oi, pcr_volume,
            COALESCE(oi_change_CE, 0) AS oi_change_CE,
            COALESCE(oi_change_PE, 0) AS oi_change_PE,
            COALESCE(volume_change_pct, 0) AS volume_change_pct,
            COALESCE(oi_change_pct, 0) AS oi_change_pct,
            COALESCE(relative_volume, 1.0) AS relative_volume,
            iv_proxy,
            COALESCE(iv_rank, 0.5) AS iv_rank,
            COALESCE(iv_percentile, 0.5) AS iv_percentile,
            COALESCE(gamma_exposure_proxy, 0) AS gamma_exposure_proxy,
            COALESCE(cum_delta_proxy, 0) AS cum_delta_proxy,
            0 AS anomaly_flag,
            0.0 AS anomaly_score,
            -1 AS cluster_kmeans,
            -1 AS cluster_dbscan,
            0.0 AS unusual_activity_score
        FROM with_lags
     """)

    # ────────────────────────────────────────────────────────────
    # Black-Scholes Option Pricing & Greeks (Vectorized Python)
    # ────────────────────────────────────────────────────────────
    print("[FEATURES] Running Black-Scholes theoretical pricing...")
    df = conn.execute("SELECT * FROM tmp_enriched").df()
    df_priced = calculate_greeks(df)
    
    # Register the dataframe and insert into final table by name
    conn.register("df_priced", df_priced)
    conn.execute("INSERT INTO options_enriched BY NAME SELECT * FROM df_priced")
    conn.execute("DROP TABLE tmp_enriched")

    count = conn.execute("SELECT COUNT(*) FROM options_enriched").fetchone()[0]
    print(f"[FEATURES] Enriched table: {count:,} rows with all computed features ✅")
    return count
