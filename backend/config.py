"""
Configuration — all tunable parameters in one place.

Override any setting via environment variables prefixed with OPTIX_,
e.g.  OPTIX_DUCKDB_PATH=./prod.duckdb
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load explicitly to ensure .env defaults override
load_dotenv()

# ── Paths ────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent          # CodeForge/
BACKEND_ROOT = Path(__file__).resolve().parent                 # CodeForge/backend/

# ── Database Connections ─────────────────────────────────────────

# PostgreSQL Connection
POSTGRES_USER: str = os.getenv("OPTIX_POSTGRES_USER", "user")
POSTGRES_PASSWORD: str = os.getenv("OPTIX_POSTGRES_PASSWORD", "password")
POSTGRES_DB: str = os.getenv("OPTIX_POSTGRES_DB", "optix")
POSTGRES_HOST: str = os.getenv("OPTIX_POSTGRES_HOST", "db")
POSTGRES_PORT: str = os.getenv("OPTIX_POSTGRES_PORT", "5432")

# DATABASE_URL for SQLAlchemy
DATABASE_URL: str = os.getenv(
    "OPTIX_DATABASE_URL",
    f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
)

# CSV data directory (contains the *_exp.csv files)
CSV_DATA_DIR: str = os.getenv(
    "OPTIX_CSV_DIR",
    str(PROJECT_ROOT / "data"),
)

# ── Anomaly Detection ────────────────────────────────────────────
ISOLATION_FOREST_CONTAMINATION: float = float(
    os.getenv("OPTIX_IF_CONTAMINATION", "0.05")
)
ISOLATION_FOREST_N_ESTIMATORS: int = int(
    os.getenv("OPTIX_IF_N_ESTIMATORS", "100")
)
ZSCORE_THRESHOLD: float = float(
    os.getenv("OPTIX_ZSCORE_THRESHOLD", "2.5")
)

# ── Clustering ───────────────────────────────────────────────────
KMEANS_N_CLUSTERS: int = int(
    os.getenv("OPTIX_KMEANS_CLUSTERS", "4")
)
DBSCAN_EPS: float = float(
    os.getenv("OPTIX_DBSCAN_EPS", "0.5")
)
DBSCAN_MIN_SAMPLES: int = int(
    os.getenv("OPTIX_DBSCAN_MIN_SAMPLES", "5")
)

# ── Rolling Windows ──────────────────────────────────────────────
ROLLING_WINDOW_SHORT: int = int(
    os.getenv("OPTIX_ROLLING_SHORT", "5")
)
ROLLING_WINDOW_MEDIUM: int = int(
    os.getenv("OPTIX_ROLLING_MEDIUM", "10")
)
ROLLING_WINDOW_LONG: int = int(
    os.getenv("OPTIX_ROLLING_LONG", "20")
)

# ── Forecasting ──────────────────────────────────────────────────
FORECAST_HORIZON: int = int(
    os.getenv("OPTIX_FORECAST_HORIZON", "10")
)

# ── Volume Spike Detection ───────────────────────────────────────
VOLUME_SPIKE_STDDEV_MULT: float = float(
    os.getenv("OPTIX_VOLUME_SPIKE_MULT", "2.0")
)

# ── Logging ──────────────────────────────────────────────────────
LOG_LEVEL: str = os.getenv("OPTIX_LOG_LEVEL", "INFO")
