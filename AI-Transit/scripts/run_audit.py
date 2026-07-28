import sys
import asyncio
sys.path.insert(0, "f:/transit-ai-system/backend")

from fastapi import Request
from app.api_routes import plan_trip, TripPlanRequestV2
from app.database.connection import SessionLocal

# Disable noisy logs
import logging
logging.getLogger("uvicorn").setLevel(logging.ERROR)
logging.getLogger("app").setLevel(logging.ERROR)

class DummyRequest(Request):
    def __init__(self):
        super().__init__({"type": "http", "headers": []})

od_pairs = [
    # Full routes
    ("1000", "20921", "21817"),
    ("1001", "21167", "24824"),
    ("1002", "20921", "21719"),
    ("1004", "20944", "23094"),
    ("1005", "21188", "21173"),
    # Half routes
    ("1000", "20921", "21138"),
    ("1002", "20921", "21864"),
    ("1004", "20944", "22192"),
]

async def run_diagnostics():
    print("Running plan_trip for multiple OD pairs to trigger diagnostics...")
    
    for route, src, dest in od_pairs:
        # TripPlanRequestV2 doesn't use the explicit TripPreferences class maybe?
        # Looking at it, preferences might just be a dict or pydantic model. We can pass a dict that fits.
        # It's better to just use a dict and let Pydantic parse it if we were calling the endpoint.
        # Since we're calling the function, we instantiate the Pydantic model directly.
        req = TripPlanRequestV2(**{
            "source_id": src,
            "destination_id": dest,
            "time_of_day": "Morning",
            "preferences": {"optimize_for": "time"}
        })
        db = SessionLocal()
        dummy_req = DummyRequest()
        try:
            await plan_trip(req=req, request=dummy_req, db=db)
        except Exception as e:
            pass
        finally:
            db.close()

if __name__ == "__main__":
    asyncio.run(run_diagnostics())
