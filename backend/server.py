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

from fastapi import FastAPI, HTTPException, Query, BackgroundTasks, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add backend/ to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from main import initialize
from services.analytics_service import AnalyticsService
from features.pricing import calculate_greeks
from auth.router import router as auth_router, get_current_user, User as AuthUser
from db.postgres import init_db, get_db, User as DBUser
import pandas as pd

from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel

app = FastAPI(
    title="OptiX API",
    description="Intelligent Options Analytics Engine",
    version="1.0.0",
)

# --- Middleware ---

class ReadinessMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # Allow access to health/root and auth routes (login/register) even if not ready
        # Or maybe just allow everything EXCEPT analysis/summary?
        # User said: "prevent repeated unauthorized requests during startup"
        # and mostly /analysis is being spammed.
        
        exempt_paths = ["/", "/docs", "/openapi.json", "/auth/login", "/auth/register", "/analysis"]
        if request.url.path not in exempt_paths and not getattr(app.state, "ready", False):
            return JSONResponse(
                status_code=503,
                content={"detail": "Backend still initializing"}
            )
        return await call_next(request)

app.add_middleware(ReadinessMiddleware)

# CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allowing all for dev, or specifically ["http://localhost:3000", "http://127.0.0.1:3000"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

import traceback
from fastapi import Request
from fastapi.responses import JSONResponse


@app.middleware("http")
async def debug_middleware(request: Request, call_next):

    try:

        response = await call_next(request)

        return response

    except Exception as e:

        print("\n\n========== BACKEND ERROR ==========")
        print("Request URL:", request.url)
        print("Request Method:", request.method)
        print("Error:", str(e))
        print("\nFull traceback:")
        traceback.print_exc()
        print("===================================\n\n")

        return JSONResponse(
            status_code=500,
            content={
                "error": str(e),
                "message": "Backend exception occurred. Check server logs."
            }
        )

# Include Auth Router
app.include_router(auth_router)

# Include Analysis Router (STEP 1 & 2)
from api.analysis_router import router as analysis_router, refresh_loop, service as shared_service

app.include_router(analysis_router)

async def run_init():
    print("[API] Starting background initialization...")
    # Initialize the shared service instance
    # Note: main.py initialize() creates a NEW AnalyticsService. 
    # We should update the shared one instead.
    # Let's adjust initialize to optionally take a service or we manually set summaries.
    new_service = await asyncio.to_thread(initialize)
    
    # Copy summaries to the shared service instance used by the router
    shared_service.set_ml_summaries(
        anomaly=new_service._anomaly_summary,
        cluster=new_service._cluster_summary,
        timeseries=new_service._timeseries_summary,
        patterns=new_service._pattern_summary
    )
    
    app.state.ready = True
    print("[API] Background initialization complete.")

@app.on_event("startup")
async def startup_event():
    # Initialize state
    app.state.ready = False
    # Initialize SQLite DB
    init_db()
    # Start the long-running pipeline in background
    asyncio.create_task(run_init())
    # Start the background refresh loop (STEP 2)
    asyncio.create_task(refresh_loop())

# --- Models ---
# (MarketSummary, PricerRequest, etc. kept as they are used by other endpoints)

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
    ce: Optional[float] = None
    pe: Optional[float] = None
    spot_close: Optional[float] = None
    atm: Optional[float] = None
    oi_ce: Optional[int] = None
    oi_pe: Optional[int] = None
    volume_ce: Optional[int] = None
    volume_pe: Optional[int] = None
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
    if not getattr(app.state, "ready", False):
        raise HTTPException(status_code=503, detail="Backend still initializing")
    return shared_service.get_market_summary()

@app.get("/insights", response_model=InsightsResponse, tags=["Analytics"])
async def get_insights(current_user: DBUser = Depends(get_current_user)):
    """Get ML-generated insights and alerts."""
    return shared_service.get_insights()

@app.get("/expiries", response_model=List[str], tags=["Metadata"])
async def get_expiries():
    """List available option expiry dates."""
    return shared_service.get_expiries()

@app.get("/strikes", response_model=List[float], tags=["Metadata"])
async def get_strikes():
    """List all unique strike prices."""
    return shared_service.get_strikes()

@app.get("/chain", response_model=List[OptionRow], tags=["Data"])
async def get_chain(
    expiry: Optional[str] = None,
    timestamp: Optional[str] = None,
    current_user: DBUser = Depends(get_current_user)
):
    """Get enriched option chain with ML filters."""
    df = shared_service.get_options_chain(timestamp, expiry)
    return df.to_dict(orient="records")

@app.get("/greeks/surface", tags=["Analytics"])
async def get_greek_surface(
    greek: str = "implied_vol",
    current_user: DBUser = Depends(get_current_user)
):
    """Get 3D surface data for a specific greek."""
    if greek not in ["implied_vol", "delta", "gamma", "vega", "theta", "vanna", "charm"]:
        raise HTTPException(status_code=400, detail="Invalid greek requested")
    
    return shared_service.get_greek_surface(greek)

@app.get("/volume/profile", tags=["Analytics"])
async def get_volume_profile(current_user: DBUser = Depends(get_current_user)):
    """Get volume and Open Interest profile by strike."""
    return shared_service.get_volume_profile()

@app.post("/pricer", tags=["Analytics"])
async def calculate_option_price(req: PricerRequest):
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
            "theo_price": row["bs_theo_ce"],
            "delta": row["bs_delta_ce"],
            "gamma": row["bs_gamma"],
            "vega": row["bs_vega"],
            "theta": row["bs_theta_ce"],
            "rho": row["bs_rho_ce"]
        },
        "put": {
            "theo_price": row["bs_theo_pe"],
            "delta": row["bs_delta_pe"],
            "gamma": row["bs_gamma"],
            "vega": row["bs_vega"],
            "theta": row["bs_theta_pe"],
            "rho": row["bs_rho_pe"]
        }
    }

@app.post("/refresh", tags=["Admin"])
async def refresh_data(
    background_tasks: BackgroundTasks,
    current_user: DBUser = Depends(get_current_user)
):
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
        summary = shared_service.get_market_summary()
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
        summary = shared_service.get_market_summary()
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
