from pydantic import BaseModel, Field, field_validator
from typing import Dict, Optional

class DemandPredictRequest(BaseModel):
    route_id: str = Field(..., min_length=1)
    hour: int = Field(..., ge=0, le=23, description="Hour must be between 0 and 23")
    weather: str
    traffic: str

    @field_validator('weather')
    @classmethod
    def validate_weather(cls, v):
        allowed = ['clear', 'cloudy', 'rainy']
        if v.lower() not in allowed:
            raise ValueError(f"Weather must be one of {allowed}")
        return v.lower()

class FleetOptimizeRequest(BaseModel):
    bus_capacity: int = Field(50, gt=0, description="Bus capacity must be > 0")
    max_buses_per_route: int = Field(10, gt=0)
    cost_per_bus: float = Field(1000.0, ge=0)
    penalty_unmet_demand: float = Field(50.0, ge=0)
    alpha: float = Field(1.0, ge=0, description="Fleet cost weight")
    beta: float = Field(2.5, ge=0, description="Efficiency penalty (waste)")
    gamma: float = Field(3.0, ge=0, description="Service penalty (unmet demand)")
    delta: float = Field(3.0, ge=0, description="Utilization penalty (<75%)")
    
class GTFSRouteDemand(BaseModel):
    route_demands: Dict[str, int]
    
    @field_validator('route_demands')
    @classmethod
    def validate_demands(cls, v):
        for route_id, demand in v.items():
            if not route_id:
                raise ValueError("route_id cannot be empty")
            if demand < 0:
                raise ValueError(f"Demand for route {route_id} cannot be negative")
        return v

class DQLTrainRequest(BaseModel):
    episodes: int = Field(500, gt=0, description="Number of episodes to train")

class DQLPredictRequest(BaseModel):
    predicted_demand: float = Field(..., ge=0)
    hour: int = Field(..., ge=0, le=23)
    weather: str = Field(...)
    traffic: str = Field(...)
    occupancy_rate: float = Field(..., ge=0, le=1)
    available_buses: int = Field(..., ge=0)

class LoginRequest(BaseModel):
    username: str
    password: str

class RegisterRequest(BaseModel):
    username: str
    password: str

class AuthMessageResponse(BaseModel):
    success: bool
    message: str

class TokenResponse(BaseModel):
    success: bool
    access_token: str
    refresh_token: str
    token_type: str
    role: str
