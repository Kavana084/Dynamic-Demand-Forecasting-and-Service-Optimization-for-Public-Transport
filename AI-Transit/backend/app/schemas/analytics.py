from pydantic import BaseModel, Field
from typing import List

class TotalPredictionsResponse(BaseModel):
    total_predictions: int = Field(..., description="Total number of prediction records")

class AverageDemandResponse(BaseModel):
    average_passenger_count: float = Field(..., description="Average predicted passenger count")

class TopRouteItem(BaseModel):
    route_id: str = Field(..., description="ID of the transit route")
    average_passenger_count: float = Field(..., description="Average predicted passenger count")

class DashboardSummaryResponse(BaseModel):
    total_predictions: int
    average_passenger_count: float
    highest_demand_route: str
    highest_demand_value: float
