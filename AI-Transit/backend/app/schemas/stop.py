# schemas/stop.py

from pydantic import BaseModel

class StopResponse(BaseModel):
    stop_id: int
    stop_name: str
    lat: float
    lon: float