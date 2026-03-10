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
                COALESCE(oi_CE, 0) + COALESCE(oi_PE, 0)         AS total_oi,
                COALESCE(volume_CE, 0) + COALESCE(volume_PE, 0) AS total_volume,

                CASE WHEN spot_close > 0
                     THEN strike / spot_close
                     ELSE NULL END                                AS moneyness,

                CASE WHEN expiry IS NOT NULL AND datetime IS NOT NULL
                     THEN CAST(EXTRACT(EPOCH FROM (expiry::timestamp - datetime)) / 86400 AS INTEGER)
                     ELSE NULL END                                AS days_to_expiry,

                CASE WHEN oi_CE > 0
                     THEN CAST(oi_PE AS DOUBLE PRECISION) / oi_CE
                     ELSE NULL END                                AS pcr_oi,

                CASE WHEN volume_CE > 0
                     THEN CAST(volume_PE AS DOUBLE PRECISION) / volume_CE
                     ELSE NULL END                                AS pcr_volume,

                CASE WHEN spot_close > 0
                     THEN (COALESCE(CE, 0) + COALESCE(PE, 0)) / spot_close * 100.0
                     ELSE 0 END                                   AS iv_proxy
            FROM options_raw
        ),
        with_lags AS (
            SELECT
                b.*,
                b.oi_CE - LAG(b.oi_CE) OVER w_se                 AS oi_change_CE,
                b.oi_PE - LAG(b.oi_PE) OVER w_se                 AS oi_change_PE,

                CASE WHEN LAG(b.total_volume) OVER w_se > 0
                     THEN (b.total_volume - LAG(b.total_volume) OVER w_se)
                           / CAST(LAG(b.total_volume) OVER w_se AS DOUBLE PRECISION) * 100.0
                     ELSE 0 END                                   AS volume_change_pct,

                CASE WHEN LAG(b.total_oi) OVER w_se > 0
                     THEN (b.total_oi - LAG(b.total_oi) OVER w_se)
                           / CAST(LAG(b.total_oi) OVER w_se AS DOUBLE PRECISION) * 100.0
                     ELSE 0 END                                   AS oi_change_pct,

                CASE WHEN AVG(b.total_volume) OVER w20_se > 0
                     THEN b.total_volume / AVG(b.total_volume) OVER w20_se
                     ELSE 1.0 END                                 AS relative_volume,

                CASE WHEN MAX(b.iv_proxy) OVER w50_se - MIN(b.iv_proxy) OVER w50_se > 0
                     THEN (b.iv_proxy - MIN(b.iv_proxy) OVER w50_se)
                         / (MAX(b.iv_proxy) OVER w50_se - MIN(b.iv_proxy) OVER w50_se)
                     ELSE 0.5 END                                 AS iv_rank,

                PERCENT_RANK() OVER w50_se                        AS iv_percentile,

                -- SQRT is not standard in SQLite, we'll approximate or handle later
                CASE WHEN b.days_to_expiry > 0
                     THEN (b.total_oi * b.spot_close * 0.0001) / 1.0 -- simplified proxy for SQLite
                     ELSE 0 END                                   AS gamma_exposure_proxy,

                CASE
                    WHEN b.moneyness < 0.97 THEN  b.oi_CE * 0.8
                    WHEN b.moneyness < 1.0  THEN  b.oi_CE * 0.5
                    WHEN b.moneyness < 1.03 THEN -b.oi_PE * 0.5
                    ELSE                         -b.oi_PE * 0.8
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
    
    # Write to final table using pandas to_sql, connection.py wrapper assumes sqlalchemy engine for .register
    # Since we are using psycopg2 cursor directly we need an engine to do pandas inserts
    # but we can reuse the sqlalchemy engine we used for register
    from db.postgres import engine
    df_priced.to_sql("options_enriched", engine, if_exists="append", index=False)
    conn.execute("DROP TABLE tmp_enriched")

    count = conn.execute("SELECT COUNT(*) FROM options_enriched").fetchone()[0]
    print(f"[FEATURES] Enriched table: {count:,} rows with all computed features ✅")
    return count
