from pydantic import BaseModel, Field
from typing import Optional, List

class FleetRecommendationRequest(BaseModel):
    route_id: str = Field(..., description="ID of the transit route")
    stop_id: str = Field(..., description="ID of the transit stop")
    bus_capacity: Optional[int] = Field(None, description="Optional bus capacity override. Defaults to config.")

class FleetRecommendationResponse(BaseModel):
    predicted_passenger_count: int = Field(..., description="Predicted number of passengers")
    bus_capacity: int = Field(..., description="Bus capacity used for calculation")
    recommended_buses: int = Field(..., description="Number of buses recommended")

class FleetOptimizationRequest(BaseModel):
    available_buses: Optional[int] = Field(None, description="Total available buses in the fleet. If not provided, dynamic logic is used based on capacity and demand or global limit.")
    bus_capacity: int = Field(60, description="Capacity per bus")
    max_buses_per_route: Optional[int] = Field(15, description="Maximum buses per route")
    cost_per_bus: Optional[float] = Field(200.0, description="Cost per bus")
    penalty_unmet_demand: Optional[float] = Field(5.0, description="Penalty for unmet demand")

class AllocatedBusItem(BaseModel):
    route_id: str = Field(..., description="ID of the transit route")
    route_name: str = Field(..., description="Name of the transit route")
    predicted_demand: int = Field(..., description="Aggregated predicted demand for this route")
    assigned_buses: int = Field(..., description="Number of buses assigned to this route")
    utilization_percent: float = Field(0.0, description="Fleet utilization percentage")
    unmet_demand: int = Field(0, description="Unserved demand")
    priority: str = Field("MEDIUM", description="Route priority level")
    recommended_frequency: str = Field("15 mins", description="Recommended frequency/headway")

class FleetOptimizationResponse(BaseModel):
    available_buses: int = Field(..., description="Total available buses in the fleet")
    used_buses: int = Field(..., description="Total buses allocated")
    total_predicted_demand: int = Field(..., description="Total demand across all routes")
    total_covered_passengers: int = Field(..., description="Total passenger demand covered by allocation")
    coverage_percentage: float = Field(..., description="Percentage of demand covered (0-100)")
    allocated_buses: List[AllocatedBusItem] = Field(..., description="Bus allocation breakdown by route")


class DemandMetrics(BaseModel):
    """
    Single source of truth for all demand-derived dashboard values.
    All dashboard cards and API responses must read from this object.
    Never recompute these fields independently.
    """
    # Raw inputs
    route_predicted_passengers: int = Field(..., description="Predicted passenger demand for the entire route")
    journey_predicted_passengers: int = Field(..., description="Estimated passengers for the selected journey segment")
    bus_capacity: int = Field(..., description="Capacity of a single bus (seated + standing)")
    available_buses: int = Field(..., description="Total buses allocated to this route")

    # Fleet allocation (based on route_predicted_passengers)
    required_buses: int = Field(..., description="ceil(route_predicted_passengers / bus_capacity)")
    allocated_buses: int = Field(..., description="min(required_buses, available_buses) — buses actually deployed")
    additional_buses_needed: int = Field(..., description="max(0, required_buses - available_buses)")
    fleet_gap: int = Field(..., description="required_buses - available_buses (negative = surplus)")

    # Occupancy (two measures, never clipped to hide reality)
    ideal_occupancy_pct: float = Field(
        ...,
        description="Occupancy if exactly required_buses are deployed (always <= 100%)"
    )
    operational_occupancy_pct: float = Field(
        ...,
        description="Actual occupancy given available_buses (may exceed 100% if shortage)"
    )

    # Demand classification — based on journey_predicted_passengers, not occupancy
    demand_level: str = Field(..., description="Low | Moderate | High | Critical")

    # Comfort — derived from operational_occupancy_pct
    crowd_level: str = Field(..., description="Low | Moderate | High | Very High")
    comfort_level: str = Field(..., description="High | Medium | Low")

    # Fleet recommendation text — strictly consistent with fleet_gap
    fleet_recommendation: str = Field(..., description="Human-readable fleet allocation recommendation")
    allocation_status: str = Field(..., description="sufficient | shortage | surplus")

