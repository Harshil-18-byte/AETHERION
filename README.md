# CodeForge: Options Analytics Platform 🚀

A high-performance options analytics dashboard for professional derivative traders. Built with a **Next.js (TypeScript)** frontend and a **FastAPI (DuckDB + ML)** analytics engine.

## 🌟 Key Features

- **Gamma Exposure (GEX)**: Real-time dealer hedging analysis and Gamma Flip level detection.
- **Volatility Regime**: IV surface analysis (Expansion/Compression/Stable detection).
- **Liquidity Clusters**: Identification of high-volume/OI concentration zones.
- **Unusual Activity**: Statistical outlier detection for options flow.
- **Market Structure**: Automated support/resistance levels from derivatives data.
- **Stability Score**: Proprietary metric (0-100) for overall market calmness.
- **Narrative Logic**: Natural language summary of current market conditions.

---

## 🛠️ Technology Stack

- **Frontend**: Next.js 16 (Turbopack), React 19, ECharts, Plotly.js, Axios.
- **Backend**: Python 3.x, FastAPI, DuckDB (OLAP Database), Scikit-Learn, Pandas.
- **Architecture**: Separated Frontend & Backend with REST API integration.

---

## 🚀 Quick Start

### 1. Prerequisites

- Node.js 18+
- Python 3.10+
- Git

### 2. Backend Setup

```bash
cd backend
pip install -r requirements.txt
python api.py
```

*The backend will initialize the database from CSV files and start on `http://localhost:8000`.*

### 3. Frontend Setup

```bash
cd frontend/options-analytics-dashboard
npm install
npm run dev
```

*The dashboard will start on `http://localhost:3000`.*

---

## 📂 Project Structure

```text
CodeForge/
├── backend/                # Python FastAPI backend
│   ├── db/                 # DuckDB schema & queries
│   ├── ingestion/          # CSV data loaders & validators
│   ├── ml/                 # Quantitative models (Anomaly, Clustering)
│   ├── services/           # Analytics Service layer
│   └── api.py              # Main REST API Entry
├── frontend/dashboard/     # Next.js Application
│   ├── charts/             # ECharts/Plotly custom components
│   ├── components/         # Shared UI components
│   └── app/                # Next.js Pages & Routes
└── data/                   # Raw options CSV datasets
```

---

## 📝 License

Proprietary. Developed for Options Market Intelligence.
