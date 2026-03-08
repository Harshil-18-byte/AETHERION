# 🚀 CodeForge Options Market Analytics Backend

This is the Python/FastAPI backend for our AI-Powered Options Market Analytics platform, built for the CodeForge Hackathon.

## 🏗️ Architecture

-   **Web Framework**: FastAPI (high performance, easy async, automatic OpenAPI docs)
-   **Data Processing**: DuckDB (blazing fast in-memory columnar processing for big data) + Polars + PyArrow
-   **Machine Learning**: `scikit-learn` & `scipy` (Isolation Forest for anomalies, K-Means for clustering hotspots, Z-scores for IV spikes)
-   **Data Structure**: All data is ingested from CSV, cleaned, and persisted in a `duckdb` database.

## 🚀 Getting Started

### Prerequisites

Ensure you have Python 3.9+ installed and pip.

### 1. Install Dependencies

```powershell
# Navigate to the backend folder
cd backend

# (Optional) Create a virtual environment
python -m venv venv
.\venv\Scripts\activate

# Install requirements
pip install -r requirements.txt
```

### 2. Load the Dataset

Before running the server, you need to ingest the options data. Place the options dataset in `data/options_data.csv`. (The dataset is expected to have columns like `date`, `act_symbol`, `expiration`, `strike`, `call_put`, `bid`, `ask`, `vol`, `open_int`, `implied_volatility`).

Run the ETL script to convert this into our high-performance DuckDB store and calculate implied features if missing:

```powershell
python -m services.etl
```

This will create `data/options.duckdb`.

### 3. Run the API Server

Start the FastAPI server:

```powershell
uvicorn main:app --reload --port 8000
```

The server will be available at: http://localhost:8000

## 🔌 API Endpoints

### Documentation
- Swagger UI (Interactive API docs): http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### 📈 Data Endpoints
- `GET /api/data/strikes` — List available strikes (with optional filters).
- `GET /api/data/expiries` — List available expiry dates (with optional filters).
- `GET /api/data/chain` — Retrieve the full options chain at a specific timestamp/date.
- `GET /api/data/timeseries` — Time-series details for a specific option contract (Underlying, Expiry, Strike, Put/Call).

### 📊 Analytics Endpoints
- `GET /api/analytics/pcr` — Put-Call Ratio over time.
- `GET /api/analytics/volatility-surface` — 3D Volatility surface point cloud for a specific underlying & date.
- `GET /api/analytics/heatmap` — Strike × Expiry OI/Volume heatmap matrix.

### 🤖 AI Endpoints
- `GET /api/ai/anomalies` — ML anomaly detection (Isolation Forest) searching for suspicious Volume, Open Interest, or Volatility changes.
- `GET /api/ai/volatility-patterns` — Volatility Skew & Smile detection.
- `GET /api/ai/iv-spikes` — Z-score detection for sudden IV spikes.
- `GET /api/ai/clusters` — K-Means market activity clustering (Low/Med/High activity hotspots).
- `GET /api/ai/insights` — Overall market insights summary.

## 🤝 Next Steps for Frontend
- Base URL is `http://localhost:8000`.
- CORS is enabled for `*` (any origin), so your local React app can access it immediately.
- Use the Swagger UI `http://localhost:8000/docs` to test endpoints and see exactly what JSON keys are returned!
