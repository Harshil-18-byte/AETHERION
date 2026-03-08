"""
Schema definition — tables, indexes, and materialized views.

Called once during initialization after data ingestion and feature engineering.
"""

from db.connection import get_connection


# ═══════════════════════════════════════════════════════════════════
# 1. RAW TABLE (populated by ingestion/loader.py)
# ═══════════════════════════════════════════════════════════════════

RAW_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS options_raw (
    symbol          VARCHAR,
    datetime        TIMESTAMP,
    expiry          DATE,
    CE              DOUBLE,      -- Call option price
    PE              DOUBLE,      -- Put option price
    spot_close      DOUBLE,      -- Underlying (NIFTY) spot price
    ATM             DOUBLE,      -- ATM strike indicator
    strike          DOUBLE,      -- Strike price
    oi_CE           BIGINT,      -- Call open interest
    oi_PE           BIGINT,      -- Put open interest
    volume_CE       BIGINT,      -- Call volume
    volume_PE       BIGINT       -- Put volume
);
"""


# ═══════════════════════════════════════════════════════════════════
# 2. ENRICHED TABLE (populated by features/engineering.py)
#    Contains all engineered features on top of raw columns.
# ═══════════════════════════════════════════════════════════════════

ENRICHED_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS options_enriched (
    -- original columns
    symbol          VARCHAR,
    datetime        TIMESTAMP,
    expiry          DATE,
    CE              DOUBLE,
    PE              DOUBLE,
    spot_close      DOUBLE,
    ATM             DOUBLE,
    strike          DOUBLE,
    oi_CE           BIGINT,
    oi_PE           BIGINT,
    volume_CE       BIGINT,
    volume_PE       BIGINT,

    -- aggregated
    total_oi        BIGINT,
    total_volume    BIGINT,

    -- moneyness & position
    moneyness       DOUBLE,      -- strike / spot_close
    days_to_expiry  INTEGER,     -- expiry - datetime::DATE

    -- ratios
    pcr_oi          DOUBLE,      -- oi_PE / oi_CE
    pcr_volume      DOUBLE,      -- volume_PE / volume_CE

    -- changes (vs previous timestamp for same strike+expiry)
    oi_change_CE    BIGINT,
    oi_change_PE    BIGINT,
    volume_change_pct DOUBLE,    -- % change in total volume
    oi_change_pct     DOUBLE,    -- % change in total OI

    -- relative metrics
    relative_volume   DOUBLE,    -- current volume / avg volume

    -- IV proxy
    iv_proxy        DOUBLE,      -- (CE + PE) / spot_close * 100

    -- IV rank & percentile (rolling)
    iv_rank         DOUBLE,
    iv_percentile   DOUBLE,

    -- greeks proxies
    gamma_exposure_proxy DOUBLE,
    cum_delta_proxy      DOUBLE,

    -- black-scholes theoretics and greeks (populated by pricing.py)
    bs_theo_CE      DOUBLE,
    bs_theo_PE      DOUBLE,
    bs_delta_CE     DOUBLE,
    bs_delta_PE     DOUBLE,
    bs_gamma        DOUBLE,
    bs_vega         DOUBLE,
    bs_theta_CE     DOUBLE,
    bs_theta_PE     DOUBLE,
    bs_rho_CE       DOUBLE,
    bs_rho_PE       DOUBLE,

    -- ML labels (populated by ml/ modules)
    anomaly_flag    INTEGER DEFAULT 0,   -- 1 = anomaly
    anomaly_score   DOUBLE  DEFAULT 0.0,
    cluster_kmeans  INTEGER DEFAULT -1,
    cluster_dbscan  INTEGER DEFAULT -1,
    unusual_activity_score DOUBLE DEFAULT 0.0
);
"""


# ═══════════════════════════════════════════════════════════════════
# 3. INDEXES for common query patterns
# ═══════════════════════════════════════════════════════════════════

INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_enr_datetime     ON options_enriched(datetime);",
    "CREATE INDEX IF NOT EXISTS idx_enr_strike       ON options_enriched(strike);",
    "CREATE INDEX IF NOT EXISTS idx_enr_expiry       ON options_enriched(expiry);",
    "CREATE INDEX IF NOT EXISTS idx_enr_dt_exp       ON options_enriched(datetime, expiry);",
    "CREATE INDEX IF NOT EXISTS idx_enr_dt_str       ON options_enriched(datetime, strike);",
    "CREATE INDEX IF NOT EXISTS idx_enr_exp_str      ON options_enriched(expiry, strike);",
    "CREATE INDEX IF NOT EXISTS idx_enr_anomaly      ON options_enriched(anomaly_flag);",
]


def create_schema() -> None:
    """Create raw + enriched tables and indexes."""
    conn = get_connection()
    conn.execute(RAW_TABLE_DDL)
    conn.execute(ENRICHED_TABLE_DDL)
    for idx_sql in INDEXES:
        conn.execute(idx_sql)
    print("[SCHEMA] Tables and indexes created ✅")


# ═══════════════════════════════════════════════════════════════════
# 4. MATERIALIZED VIEWS (re-created tables in SQLite)
# ═══════════════════════════════════════════════════════════════════

MATERIALIZED_VIEWS = {

    # (a) Volatility surface
    "mv_volatility_surface": """
        CREATE TABLE mv_volatility_surface AS
        SELECT
            strike,
            expiry,
            AVG(iv_proxy)          AS avg_iv,
            MIN(iv_proxy)          AS min_iv,
            MAX(iv_proxy)          AS max_iv,
            0                      AS std_iv, -- SQLite lacks native STDDEV
            COUNT(*)               AS obs_count
        FROM options_enriched
        GROUP BY strike, expiry
    """,

    # (b) OI distribution
    "mv_oi_distribution": """
        CREATE TABLE mv_oi_distribution AS
        WITH latest AS (
            SELECT expiry, MAX(datetime) AS max_dt
            FROM options_enriched
            GROUP BY expiry
        )
        SELECT
            e.strike,
            e.expiry,
            e.oi_CE,
            e.oi_PE,
            e.total_oi,
            e.pcr_oi,
            e.datetime
        FROM options_enriched e
        JOIN latest l ON e.expiry = l.expiry AND e.datetime = l.max_dt
    """,

    # (c) Volume aggregated across 5-minute windows
    "mv_volume_timeseries": """
        CREATE TABLE mv_volume_timeseries AS
        SELECT
            datetime(
                strftime('%s', datetime) - (strftime('%s', datetime) % 300),
                'unixepoch'
            ) AS bucket,
            expiry,
            SUM(volume_CE)   AS total_vol_CE,
            SUM(volume_PE)   AS total_vol_PE,
            SUM(total_volume) AS total_vol,
            AVG(spot_close)   AS avg_spot,
            COUNT(DISTINCT strike) AS n_strikes
        FROM options_enriched
        GROUP BY bucket, expiry
    """,

    # (d) Put-call ratio across strikes
    "mv_pcr_by_strike": """
        CREATE TABLE mv_pcr_by_strike AS
        WITH latest AS (
            SELECT expiry, MAX(datetime) AS max_dt
            FROM options_enriched
            GROUP BY expiry
        )
        SELECT
            e.strike,
            e.expiry,
            e.pcr_oi,
            e.pcr_volume,
            e.oi_CE,
            e.oi_PE,
            e.volume_CE,
            e.volume_PE
        FROM options_enriched e
        JOIN latest l ON e.expiry = l.expiry AND e.datetime = l.max_dt
    """,

    # (e) Rolling statistics
    "mv_rolling_stats": """
        CREATE TABLE mv_rolling_stats AS
        SELECT
            datetime,
            strike,
            expiry,
            iv_proxy,
            total_oi,
            total_volume,
            AVG(iv_proxy)  OVER w5  AS iv_ma5,
            AVG(iv_proxy)  OVER w10 AS iv_ma10,
            AVG(iv_proxy)  OVER w20 AS iv_ma20,
            0                OVER w20 AS iv_std20, -- SQLite lacks native STDDEV
            AVG(total_oi)    OVER w5  AS oi_ma5,
            AVG(total_volume) OVER w5 AS vol_ma5,
            spot_close
        FROM options_enriched
        WINDOW
            w5  AS (PARTITION BY strike, expiry ORDER BY datetime ROWS BETWEEN 4 PRECEDING AND CURRENT ROW),
            w10 AS (PARTITION BY strike, expiry ORDER BY datetime ROWS BETWEEN 9 PRECEDING AND CURRENT ROW),
            w20 AS (PARTITION BY strike, expiry ORDER BY datetime ROWS BETWEEN 19 PRECEDING AND CURRENT ROW)
    """,

    # (f) Anomaly flags snapshot
    "mv_anomaly_summary": """
        CREATE TABLE mv_anomaly_summary AS
        SELECT
            datetime,
            strike,
            expiry,
            iv_proxy,
            total_volume,
            total_oi,
            anomaly_flag,
            anomaly_score,
            unusual_activity_score,
            spot_close,
            moneyness,
            cluster_kmeans,
            cluster_dbscan
        FROM options_enriched
        WHERE anomaly_flag = 1
           OR unusual_activity_score > 0.5
    """,

    # (g) Max-pain helper
    "mv_max_pain": """
        CREATE TABLE mv_max_pain AS
        WITH latest AS (
            SELECT expiry, MAX(datetime) AS max_dt
            FROM options_enriched
            GROUP BY expiry
        ),
        chain AS (
            SELECT e.strike, e.expiry, e.oi_CE, e.oi_PE
            FROM options_enriched e
            JOIN latest l ON e.expiry = l.expiry AND e.datetime = l.max_dt
        ),
        all_strikes AS (
            SELECT DISTINCT strike AS settlement FROM chain
        )
        SELECT
            c.expiry,
            s.settlement AS settlement_price,
            SUM(
                CASE WHEN s.settlement > c.strike
                     THEN (s.settlement - c.strike) * c.oi_CE
                     ELSE 0 END
            ) AS call_liability,
            SUM(
                CASE WHEN s.settlement < c.strike
                     THEN (c.strike - s.settlement) * c.oi_PE
                     ELSE 0 END
            ) AS put_liability,
            SUM(
                CASE WHEN s.settlement > c.strike
                     THEN (s.settlement - c.strike) * c.oi_CE
                     ELSE 0 END
            ) + SUM(
                CASE WHEN s.settlement < c.strike
                     THEN (c.strike - s.settlement) * c.oi_PE
                     ELSE 0 END
            ) AS total_liability
        FROM chain c
        CROSS JOIN all_strikes s
        GROUP BY c.expiry, s.settlement
    """,
}


def create_materialized_views() -> None:
    """Create (or replace) tables from enriched data (SQLite compatible)."""
    conn = get_connection()
    for name, sql in MATERIALIZED_VIEWS.items():
        conn.execute(f"DROP TABLE IF EXISTS {name}")
        conn.execute(sql)
        count = conn.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
        print(f"  [MV] {name}: {count:,} rows")
    print("[SCHEMA] All pre-computed tables created ✅")
