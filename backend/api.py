"""
OptiX API -- FastAPI Server

Provides REST endpoints for the OptiX frontend.
Bridges the AnalyticsService (DuckDB + ML) to the web.
"""

import sys
import os
import random
import asyncio
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, HTTPException, Query, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add backend/ to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from main import initialize
from services.analytics_service import AnalyticsService
from features.pricing import calculate_greeks
import pandas as pd

# Initialize the full backend pipeline
service: AnalyticsService = initialize()

app = FastAPI(
    title="OptiX API",
    description="Intelligent Options Analytics Engine",
    version="1.0.0",
)

# CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Models ---

class MarketSummary(BaseModel):
    timestamp: str
    spot_price: float
    avg_iv: float
    total_oi: int
    total_volume: int
    overall_pcr: float
    anomaly_count: int
    active_expiries: int
    active_strikes: int

class PricerRequest(BaseModel):
    spot: float
    strike: float
    dte: float
    iv: float # raw decimal (e.g. 0.20 for 20%)
    risk_free_rate: float = 0.05

class Insight(BaseModel):
    category: str
    text: str
    severity: str

class InsightsResponse(BaseModel):
    timestamp: str
    spot_price: float
    total_insights: int
    insights: List[Insight]

class OptionRow(BaseModel):
    symbol: Optional[str] = None
    datetime: Optional[str] = None
    expiry: Optional[str] = None
    strike: Optional[float] = None
    CE: Optional[float] = None
    PE: Optional[float] = None
    spot_close: Optional[float] = None
    ATM: Optional[float] = None
    oi_CE: Optional[int] = None
    oi_PE: Optional[int] = None
    volume_CE: Optional[int] = None
    volume_PE: Optional[int] = None
    total_oi: Optional[int] = None
    total_volume: Optional[int] = None
    iv_proxy: Optional[float] = None
    pcr_oi: Optional[float] = None
    pcr_volume: Optional[float] = None
    moneyness: Optional[float] = None
    days_to_expiry: Optional[int] = None
    anomaly_flag: Optional[int] = 0
    cluster_kmeans: Optional[int] = -1
    unusual_activity_score: Optional[float] = 0.0

# --- Endpoints ---

@app.get("/", tags=["Health"])
async def root():
    return {"status": "online", "engine": "OptiX", "version": "1.0.0"}

@app.get("/summary", response_model=MarketSummary, tags=["Analytics"])
async def get_summary():
    """Get overall market snapshot."""
    return service.get_market_summary()

@app.get("/insights", response_model=InsightsResponse, tags=["Analytics"])
async def get_insights():
    """Get ML-generated insights and alerts."""
    return service.get_insights()

@app.get("/expiries", response_model=List[str], tags=["Metadata"])
async def get_expiries():
    """List available option expiry dates."""
    return service.get_expiries()

@app.get("/strikes", response_model=List[float], tags=["Metadata"])
async def get_strikes():
    """List all unique strike prices."""
    return service.get_strikes()

@app.get("/chain", response_model=List[OptionRow], tags=["Data"])
async def get_chain(
    expiry: Optional[str] = None,
    timestamp: Optional[str] = None
):
    """Get enriched option chain with ML filters."""
    df = service.get_options_chain(timestamp, expiry)
    return df.to_dict(orient="records")

@app.get("/greeks/surface", tags=["Analytics"])
async def get_greek_surface(greek: str = "implied_vol"):
    """Get 3D surface data for a specific greek."""
    if greek not in ["implied_vol", "delta", "gamma", "vega", "theta", "vanna", "charm"]:
        raise HTTPException(status_code=400, detail="Invalid greek requested")
    
    return service.get_greek_surface(greek)

@app.get("/volume/profile", tags=["Analytics"])
async def get_volume_profile():
    """Get volume and Open Interest profile by strike."""
    return service.get_volume_profile()

@app.post("/pricer", tags=["Analytics"])
async def calulate_option_price(req: PricerRequest):
    """Calculate theoretical option prices and Greeks using BSM on the fly."""
    df = pd.DataFrame([{
        "spot_close": req.spot,
        "strike": req.strike,
        "days_to_expiry": req.dte,
        "iv_proxy": req.iv * 100.0  # expects percentage format internally
    }])
    df_priced = calculate_greeks(df, risk_free_rate=req.risk_free_rate)
    row = df_priced.iloc[0]
    
    return {
        "call": {
            "theo_price": row["bs_theo_CE"],
            "delta": row["bs_delta_CE"],
            "gamma": row["bs_gamma"],
            "vega": row["bs_vega"],
            "theta": row["bs_theta_CE"],
            "rho": row["bs_rho_CE"]
        },
        "put": {
            "theo_price": row["bs_theo_PE"],
            "delta": row["bs_delta_PE"],
            "gamma": row["bs_gamma"],
            "vega": row["bs_vega"],
            "theta": row["bs_theta_PE"],
            "rho": row["bs_rho_PE"]
        }
    }

@app.post("/refresh", tags=["Admin"])
async def refresh_data(background_tasks: BackgroundTasks):
    """Trigger a full data reload and re-run ML pipeline."""
    global service
    background_tasks.add_task(initialize)
    return {"message": "Refresh started in background"}

# --- WebSockets ---

def _generate_tape_print(spot: float):
    """Helper to generate a random live tape print."""
    is_call = random.random() > 0.45
    opt_type = "CALL" if is_call else "PUT"
    
    # Strike near spot
    strike_offset = random.randint(-5, 5) * 100
    strike = round(spot / 100) * 100 + strike_offset
    
    size = random.randint(10, 1500)
    # Simple fake price based on distance from ATM
    dist = abs(strike - spot)
    price = max(0.05, 100 - (dist * 0.05) + random.uniform(-2, 2))
    
    sentiment = "BULLISH" if (is_call and random.random()>0.3) or (not is_call and random.random()>0.7) else "BEARISH"
    
    return {
        "id": f"tp_{random.randint(10000, 99999)}",
        "time": datetime.now().strftime("%I:%M:%S %p"),
        "strike": strike,
        "type": opt_type,
        "size": size,
        "price": price,
        "sentiment": sentiment
    }

@app.websocket("/ws/tape")
async def websocket_tape(websocket: WebSocket):
    """Stream simulated live options trades."""
    await websocket.accept()
    try:
        # Get current spot to anchor the fake trades
        summary = service.get_market_summary()
        spot = summary.get("spot_price", 25000)
        
        while True:
            # Yield 1-3 prints per tick
            batch = [_generate_tape_print(spot) for _ in range(random.randint(1, 3))]
            await websocket.send_json(batch)
            # Sleep 0.5 to 3.0 seconds
            await asyncio.sleep(random.uniform(0.5, 3.0))
    except WebSocketDisconnect:
        print("Client disconnected from /ws/tape")

def _generate_darkpool_print(spot: float):
    """Helper to generate a random dark pool print."""
    volume = random.randint(100_000, 2_500_000)
    # Price variation near spot
    price = spot * (1 + random.uniform(-0.005, 0.005))
    est_value = (volume * price) / 1_000_000  # in Millions
    
    return {
        "id": f"dp_{random.randint(1000, 9999)}",
        "time": datetime.now().strftime("%I:%M:%S %p"),
        "volume": volume,
        "price": price,
        "estimated_value": round(est_value, 2)
    }

@app.websocket("/ws/darkpool")
async def websocket_darkpool(websocket: WebSocket):
    """Stream simulated dark pool block prints."""
    await websocket.accept()
    try:
        summary = service.get_market_summary()
        spot = summary.get("spot_price", 25000)
        
        while True:
            # Dark pool prints are less frequent
            print_obj = [_generate_darkpool_print(spot)]
            await websocket.send_json(print_obj)
            # Sleep 4.0 to 10.0 seconds
            await asyncio.sleep(random.uniform(4.0, 10.0))
    except WebSocketDisconnect:
        print("Client disconnected from /ws/darkpool")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
