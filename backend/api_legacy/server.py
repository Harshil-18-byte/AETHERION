from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from main import initialize
from typing import Optional

# Global service instance
service: Optional[object] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global service
    print("[API] Initializing heavy services...")
    service = initialize()
    yield
    print("[API] Shutting down...")

app = FastAPI(title="OptiX Backend", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allowing all for dev, or specifically ["http://localhost:3000", "http://127.0.0.1:3000"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"status": "OptiX backend running"}

@app.get("/analysis")
def get_analysis():
    if service is None:
        return {"error": "Service not ready"}
    return service.get_market_summary()

@app.post("/analysis")
async def post_analysis(file: UploadFile = File(...)):
    if service is None:
        return {"error": "Service not ready"}
    # For now, just return a dummy success message as requested by the task
    # (The frontend expects a valid AnalysisResponse which service.get_market_summary() provides)
    return service.get_market_summary()