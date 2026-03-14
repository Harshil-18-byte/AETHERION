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

    # Clear enriched table
    conn.execute("DELETE FROM options_enriched")

    # SQLite compatible Engineering SQL
    conn.execute("""
        CREATE TEMP TABLE tmp_enriched AS
        WITH base AS (
            SELECT
                *,
                COALESCE(oi_ce, 0) + COALESCE(oi_pe, 0)         AS total_oi,
                COALESCE(volume_ce, 0) + COALESCE(volume_pe, 0) AS total_volume,

                CASE WHEN spot_close > 0
                     THEN strike / spot_close
                     ELSE NULL END                                AS moneyness,

                -- Simplified date diff for SQLite (days)
                CASE WHEN expiry IS NOT NULL AND datetime IS NOT NULL
                     THEN CAST((julianday(expiry) - julianday(datetime)) AS INTEGER)
                     ELSE NULL END                                AS days_to_expiry,

                CASE WHEN oi_ce > 0
                     THEN CAST(oi_pe AS REAL) / oi_ce
                     ELSE NULL END                                AS pcr_oi,

                CASE WHEN volume_ce > 0
                     THEN CAST(volume_pe AS REAL) / volume_ce
                     ELSE NULL END                                AS pcr_volume,

                CASE WHEN spot_close > 0
                     THEN (COALESCE(ce, 0) + COALESCE(pe, 0)) / spot_close * 100.0
                     ELSE 0 END                                   AS iv_proxy
            FROM options_raw
        ),
        with_lags AS (
            SELECT
                b.*,
                b.oi_ce - LAG(b.oi_ce) OVER w_se                 AS oi_change_ce,
                b.oi_pe - LAG(b.oi_pe) OVER w_se                 AS oi_change_pe,

                CASE WHEN LAG(b.total_volume) OVER w_se > 0
                     THEN (b.total_volume - LAG(b.total_volume) OVER w_se)
                           / CAST(LAG(b.total_volume) OVER w_se AS REAL) * 100.0
                     ELSE 0 END                                   AS volume_change_pct,

                CASE WHEN LAG(b.total_oi) OVER w_se > 0
                     THEN (b.total_oi - LAG(b.total_oi) OVER w_se)
                           / CAST(LAG(b.total_oi) OVER w_se AS REAL) * 100.0
                     ELSE 0 END                                   AS oi_change_pct,

                CASE WHEN AVG(b.total_volume) OVER w20_se > 0
                     THEN b.total_volume / AVG(b.total_volume) OVER w20_se
                     ELSE 1.0 END                                 AS relative_volume,

                CASE WHEN MAX(b.iv_proxy) OVER w50_se - MIN(b.iv_proxy) OVER w50_se > 0
                     THEN (b.iv_proxy - MIN(b.iv_proxy) OVER w50_se)
                         / (MAX(b.iv_proxy) OVER w50_se - MIN(b.iv_proxy) OVER w50_se)
                     ELSE 0.5 END                                 AS iv_rank,

                -- SQLite doesn't have standard PERCENT_RANK() in all versions or builds, 
                -- or it might be complex. Using simplified percentile proxy.
                0.5                                               AS iv_percentile,

                CASE WHEN b.days_to_expiry > 0
                     THEN (b.total_oi * b.spot_close * 0.0001) / 1.0 
                     ELSE 0 END                                   AS gamma_exposure_proxy,

                CASE
                    WHEN b.moneyness < 0.97 THEN  b.oi_ce * 0.8
                    WHEN b.moneyness < 1.0  THEN  b.oi_ce * 0.5
                    WHEN b.moneyness < 1.03 THEN -b.oi_pe * 0.5
                    ELSE                         -b.oi_pe * 0.8
                END                                               AS cum_delta_proxy

            FROM base b
            WINDOW
                w_se     AS (PARTITION BY b.strike, b.expiry ORDER BY b.datetime),
                w20_se   AS (PARTITION BY b.strike, b.expiry ORDER BY b.datetime
                             ROWS BETWEEN 19 PRECEDING AND CURRENT ROW),
                w50_se   AS (PARTITION BY b.strike, b.expiry ORDER BY b.datetime
                             ROWS BETWEEN 49 PRECEDING AND CURRENT ROW)
        )
        SELECT * FROM with_lags
    """)

    print("[FEATURES] Running Black-Scholes theoretical pricing...")
    df = conn.execute("SELECT * FROM tmp_enriched").df()
    df_priced = calculate_greeks(df)
    
    # Write to final table
    from db.postgres import engine
    df_priced.to_sql("options_enriched", engine, if_exists="append", index=False)
    conn.execute("DROP TABLE tmp_enriched")

    count = conn.execute("SELECT COUNT(*) FROM options_enriched").fetchone()[0]
    print(f"[FEATURES] Enriched table: {count:,} rows with all computed features ✅")
    return count
