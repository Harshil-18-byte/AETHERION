from fastapi import APIRouter
from fastapi.responses import JSONResponse
from datetime import datetime
import asyncio
import logging

from services.analytics_service import AnalyticsService

router = APIRouter()
# Note: We should ideally inject this or use a shared instance if initialization is heavy 
# and happened in server.py. For now, following user's structure.
service = AnalyticsService()

logger = logging.getLogger("analysis")

analysis_cache = {
    "timestamp": None,
    "data": None
}

cache_lock = asyncio.Lock()


async def update_cache():

    global analysis_cache

    async with cache_lock:

        try:

            logger.info("Updating analysis cache")

            # This might fail if database isn't ready or empty
            result = service.get_full_analysis()

            analysis_cache = {
                "timestamp": datetime.utcnow().isoformat(),
                "data": result
            }

            logger.info("Cache updated")

        except Exception as e:

            logger.error("Cache update failed", exc_info=True)


@router.get("/analysis")
async def get_analysis(expiry: str | None = None):

    global analysis_cache

    try:

        if analysis_cache["data"] is None:
            await update_cache()

        return {
            "expiries": service.get_expiries(),
            "selected_expiry": expiry,
            "analysis": analysis_cache["data"]
        }

    except Exception as e:

        logger.error("Analysis endpoint failed", exc_info=True)

        return JSONResponse(
            status_code=200,
            content={
                "expiries": [],
                "selected_expiry": expiry,
                "analysis": {}
            }
        )


async def refresh_loop():

    while True:

        try:
            await update_cache()
        except Exception:
            pass

        await asyncio.sleep(30)
