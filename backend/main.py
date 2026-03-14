"""
OptiX Backend -- Main Entry Point

Orchestrates the full initialization pipeline:
  1. Create DB schema
  2. Load CSVs -> DuckDB
  3. Validate data quality
  4. Run feature engineering
  5. Run ML pipeline (anomaly, clustering, time-series, patterns)
  6. Build materialized views
  7. Return an initialized AnalyticsService

Usage:
    python main.py                  # standalone smoke test
    from main import initialize     # import for FastAPI / Streamlit
"""

import sys
import os
import time
from pathlib import Path

# Force UTF-8 on Windows terminals
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Add backend/ to path so that submodule imports work
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import LOG_LEVEL
from db.connection import get_connection, close_connection
from db.schema import create_schema, create_materialized_views
from ingestion.loader import load_csv_to_sqlite
from ingestion.validator import validate_data
from features.engineering import run_feature_engineering
from ml.anomaly import run_anomaly_detection
from ml.clustering import run_clustering
from ml.timeseries import run_timeseries_analysis
from ml.patterns import run_pattern_detection
from services.analytics_service import AnalyticsService


def initialize() -> AnalyticsService:
    """
    Run the full pipeline and return a ready-to-use AnalyticsService.
    Idempotent: can be called multiple times for data refreshes.
    """
    t0 = time.perf_counter()
    print("")
    print("=" * 56)
    print("  OptiX Backend -- Initialization")
    print("=" * 56)
    print("")

    # Step 0: Check DB Connection
    print("[0/7] Checking SQLite connection...")
    try:
        from db.connection import get_connection
        conn = get_connection()
        conn.execute("SELECT 1")
        print("  ✅ SQLite connection successful.")
    except Exception as e:
        print(f"  ❌ SQLite connection failed: {e}")
        raise RuntimeError(f"Database unavailable: {e}")

    # Step 1: Schema
    print("[1/7] Creating schema...")
    create_schema()

    # Step 2: Load CSVs
    print("[2/7] Loading CSV data...")
    total_rows = load_csv_to_sqlite()

    # Step 3: Validate
    print("[3/7] Validating data quality...")
    quality = validate_data()

    # Step 4: Feature Engineering
    print("[4/7] Running feature engineering...")
    enriched_rows = run_feature_engineering()

    # Step 5: ML Pipeline
    print("[5/7] Running ML pipeline...")
    print("  - Anomaly detection...")
    anomaly_summary = run_anomaly_detection()

    print("  - Clustering...")
    cluster_summary = run_clustering()

    print("  - Time-series analysis...")
    ts_summary = run_timeseries_analysis()

    print("  - Pattern detection...")
    pattern_summary = run_pattern_detection()

    # Step 6: Materialized Views
    print("[6/7] Building materialized views...")
    create_materialized_views()

    # Step 7: Wire up service
    print("[7/7] Initializing service layer...")
    service = AnalyticsService()
    service.set_ml_summaries(
        anomaly=anomaly_summary,
        cluster=cluster_summary,
        timeseries=ts_summary,
        patterns=pattern_summary,
    )

    elapsed = time.perf_counter() - t0
    print("")
    print("=" * 56)
    print(f"  Backend initialized in {elapsed:.2f}s")
    print(f"  {enriched_rows:,} enriched rows ready")
    print(f"  {anomaly_summary.get('combined_anomalies', 0):,} anomalies flagged")
    print(f"  {cluster_summary.get('kmeans_clusters', 0)} clusters formed")
    print(f"  {len(ts_summary.get('iv_trends', []))} expiry trends")
    print(f"  {len(pattern_summary.get('max_pain', []))} max-pain levels")
    print("=" * 56)
    print("")

    return service


# -- Standalone smoke test --
if __name__ == "__main__":
    svc = initialize()

    # Quick verification
    print("Smoke Test:")
    print(f"   Row count:   {svc.get_row_count():,}")
    print(f"   Expiries:    {svc.get_expiries()}")
    print(f"   Strikes:     {len(svc.get_strikes())} unique")

    summary = svc.get_market_summary()
    print(f"   Spot:        {summary['spot_price']:,.2f}")
    print(f"   Avg IV:      {summary['avg_iv']:.4f}")
    print(f"   Total OI:    {summary['total_oi']:,}")
    print(f"   PCR:         {summary['overall_pcr']:.4f}")

    # Insights
    insights = svc.get_insights()
    print(f"\n{insights['total_insights']} insights generated:")
    for ins in insights["insights"][:5]:
        print(f"   [{ins['severity'].upper()}] {ins['category']}: {ins['text']}")

    close_connection()
    print("\nAll smoke tests passed!")
