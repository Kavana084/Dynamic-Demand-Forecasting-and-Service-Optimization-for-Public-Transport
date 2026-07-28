from pydantic import BaseModel, Field

class ForecastRequest(BaseModel):
    route_id: str = Field(..., description="ID of the transit route")
    stop_id: str = Field(..., description="ID of the transit stop")

class ForecastResponse(BaseModel):
    predicted_passenger_count: int = Field(..., description="Predicted number of passengers")