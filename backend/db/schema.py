"""
Schema definition — tables, indexes, and materialized views for PostgreSQL.

Called once during initialization after data ingestion and feature engineering.
"""

from db.connection import get_connection


# ═══════════════════════════════════════════════════════════════════
# 1. RAW TABLE (populated by ingestion/loader.py)
# ═══════════════════════════════════════════════════════════════════

RAW_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS options_raw (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol          VARCHAR(50),
    datetime        TIMESTAMP,
    expiry          DATE,
    ce              REAL,
    pe              REAL,
    spot_close      REAL,
    atm             REAL,
    strike          REAL,
    oi_ce           BIGINT,
    oi_pe           BIGINT,
    volume_ce       BIGINT,
    volume_pe       BIGINT
);
"""


# ═══════════════════════════════════════════════════════════════════
# 2. ENRICHED TABLE (populated by features/engineering.py)
#    Contains all engineered features on top of raw columns.
# ═══════════════════════════════════════════════════════════════════

ENRICHED_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS options_enriched (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    -- original columns
    symbol          VARCHAR(50),
    datetime        TIMESTAMP,
    expiry          DATE,
    ce              REAL,
    pe              REAL,
    spot_close      REAL,
    atm             REAL,
    strike          REAL,
    oi_ce           BIGINT,
    oi_pe           BIGINT,
    volume_ce       BIGINT,
    volume_pe       BIGINT,

    -- aggregated
    total_oi        BIGINT,
    total_volume    BIGINT,

    -- moneyness & position
    moneyness       REAL,
    days_to_expiry  INTEGER,

    -- ratios
    pcr_oi          REAL,
    pcr_volume      REAL,

    -- changes
    oi_change_ce    BIGINT,
    oi_change_pe    BIGINT,
    volume_change_pct REAL,
    oi_change_pct     REAL,

    -- relative metrics
    relative_volume   REAL,

    -- IV proxy
    iv_proxy        REAL,

    -- IV rank & percentile
    iv_rank         REAL,
    iv_percentile   REAL,

    -- greeks proxies
    gamma_exposure_proxy REAL,
    cum_delta_proxy      REAL,

    -- black-scholes
    bs_theo_ce      REAL,
    bs_theo_pe      REAL,
    bs_delta_ce     REAL,
    bs_delta_pe     REAL,
    bs_gamma        REAL,
    bs_vega         REAL,
    bs_theta_ce     REAL,
    bs_theta_pe     REAL,
    bs_rho_ce       REAL,
    bs_rho_pe       REAL,

    -- ML labels
    anomaly_flag    INTEGER DEFAULT 0,
    anomaly_score   REAL  DEFAULT 0.0,
    cluster_kmeans  INTEGER DEFAULT -1,
    cluster_dbscan  INTEGER DEFAULT -1,
    unusual_activity_score REAL DEFAULT 0.0
);
"""


# ═══════════════════════════════════════════════════════════════════
# 3. INDEXES
# ═══════════════════════════════════════════════════════════════════

INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_options_expiry_datetime ON options_enriched(expiry, datetime);",
    "CREATE INDEX IF NOT EXISTS idx_options_strike ON options_enriched(strike);",
    "CREATE INDEX IF NOT EXISTS idx_options_datetime ON options_enriched(datetime);",
    "CREATE INDEX IF NOT EXISTS idx_enr_dt_exp ON options_enriched(datetime, expiry);",
    "CREATE INDEX IF NOT EXISTS idx_enr_anomaly ON options_enriched(anomaly_flag);",
]


def create_schema() -> None:
    """Create raw + enriched tables and indexes."""
    conn = get_connection()
    conn.execute("DROP TABLE IF EXISTS options_raw")
    conn.execute("DROP TABLE IF EXISTS options_enriched")
    conn.execute(RAW_TABLE_DDL)
    conn.execute(ENRICHED_TABLE_DDL)
    for idx_sql in INDEXES:
        conn.execute(idx_sql)
    print("[SCHEMA] Tables and indexes created ✅")


# ═══════════════════════════════════════════════════════════════════
# 4. MATERIALIZED VIEWS (re-created as real tables for speed in analytics)
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
            -- SQLite doesn't have standard STDDEV, approximating with: sqrt(avg(x*x) - avg(x)*avg(x))
            SQRT(AVG(iv_proxy * iv_proxy) - AVG(iv_proxy) * AVG(iv_proxy)) AS std_iv,
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
            e.oi_ce,
            e.oi_pe,
            e.total_oi,
            e.pcr_oi,
            e.datetime
        FROM options_enriched e
        JOIN latest l ON e.expiry = l.expiry AND e.datetime = l.max_dt
    """,

    # (c) Volume timeseries (5-minute buckets)
    "mv_volume_timeseries": """
        CREATE TABLE mv_volume_timeseries AS
        SELECT
            strftime('%Y-%m-%d %H:%M:00', datetime) AS bucket,
            expiry,
            SUM(volume_ce)   AS total_vol_ce,
            SUM(volume_pe)   AS total_vol_pe,
            SUM(total_volume) AS total_vol,
            AVG(spot_close)   AS avg_spot,
            COUNT(DISTINCT strike) AS n_strikes
        FROM options_enriched
        GROUP BY bucket, expiry
    """,

    # (d) Put-call ratio
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
            e.oi_ce,
            e.oi_pe,
            e.volume_ce,
            e.volume_pe
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
            -- Simplified window functions for SQLite
            AVG(iv_proxy)  OVER (PARTITION BY strike, expiry ORDER BY datetime ROWS BETWEEN 4 PRECEDING AND CURRENT ROW) AS iv_ma5,
            AVG(iv_proxy)  OVER (PARTITION BY strike, expiry ORDER BY datetime ROWS BETWEEN 9 PRECEDING AND CURRENT ROW) AS iv_ma10,
            AVG(iv_proxy)  OVER (PARTITION BY strike, expiry ORDER BY datetime ROWS BETWEEN 19 PRECEDING AND CURRENT ROW) AS iv_ma20,
            -- Rolling Standard Deviation Approximation
            SQRT(
                AVG(iv_proxy * iv_proxy) OVER (PARTITION BY strike, expiry ORDER BY datetime ROWS BETWEEN 19 PRECEDING AND CURRENT ROW) -
                (AVG(iv_proxy) OVER (PARTITION BY strike, expiry ORDER BY datetime ROWS BETWEEN 19 PRECEDING AND CURRENT ROW) * 
                 AVG(iv_proxy) OVER (PARTITION BY strike, expiry ORDER BY datetime ROWS BETWEEN 19 PRECEDING AND CURRENT ROW))
            ) AS iv_std20,
            AVG(total_oi)  OVER (PARTITION BY strike, expiry ORDER BY datetime ROWS BETWEEN 4 PRECEDING AND CURRENT ROW) AS oi_ma5,
            AVG(total_volume) OVER (PARTITION BY strike, expiry ORDER BY datetime ROWS BETWEEN 4 PRECEDING AND CURRENT ROW) AS vol_ma5,
            spot_close
        FROM options_enriched
    """,

    # (f) Anomaly summary
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

    # (g) Max Pain
    "mv_max_pain": """
        CREATE TABLE mv_max_pain AS
        WITH latest AS (
            SELECT expiry, MAX(datetime) AS max_dt
            FROM options_enriched
            GROUP BY expiry
        ),
        chain AS (
            SELECT e.strike, e.expiry, e.oi_ce, e.oi_pe
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
                     THEN (s.settlement - c.strike) * c.oi_ce
                     ELSE 0 END
            ) AS call_liability,
            SUM(
                CASE WHEN s.settlement < c.strike
                     THEN (c.strike - s.settlement) * c.oi_pe
                     ELSE 0 END
            ) AS put_liability,
            SUM(
                CASE WHEN s.settlement > c.strike
                     THEN (s.settlement - c.strike) * c.oi_ce
                     ELSE 0 END
            ) + SUM(
                CASE WHEN s.settlement < c.strike
                     THEN (c.strike - s.settlement) * c.oi_pe
                     ELSE 0 END
            ) AS total_liability
        FROM chain c
        CROSS JOIN all_strikes s
        GROUP BY c.expiry, s.settlement
    """,
}


def create_materialized_views() -> None:
    """Create (or replace) tables from enriched data."""
    conn = get_connection()
    for name, sql in MATERIALIZED_VIEWS.items():
        conn.execute(f"DROP TABLE IF EXISTS {name}")
        conn.execute(sql)
        count = conn.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
        print(f"  [MV] {name}: {count:,} rows")
    print("[SCHEMA] All pre-computed tables created ✅")
