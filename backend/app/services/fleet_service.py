import logging
import math
from sqlalchemy.orm import Session
from app.schemas.fleet import FleetRecommendationRequest, FleetRecommendationResponse
from app.schemas.forecast import ForecastRequest
from app.services.forecast_service import ForecastService
from app.config import settings

logger = logging.getLogger(__name__)

class FleetService:
    @staticmethod
    def generate_recommendation(db: Session, request: FleetRecommendationRequest) -> FleetRecommendationResponse:
        logger.info(f"Generating fleet recommendation for route_id={request.route_id}, stop_id={request.stop_id}")
        
        # 1. Use ForecastService logic to predict passenger count
        forecast_request = ForecastRequest(
            route_id=request.route_id,
            stop_id=request.stop_id
        )
        predicted_count = ForecastService.generate_forecast(db, forecast_request)
        
        # 2. Determine capacity (use override if provided, else config default)
        capacity = request.bus_capacity if request.bus_capacity is not None else settings.default_bus_capacity
        
        # 3. Calculate recommended buses
        if capacity <= 0:
            logger.error(f"Invalid bus capacity provided: {capacity}")
            raise ValueError("Bus capacity must be greater than zero")
            
        recommended_buses = math.ceil(predicted_count / capacity)
        
        logger.info(f"Recommended {recommended_buses} buses (capacity: {capacity}) for {predicted_count} passengers.")
        
        return FleetRecommendationResponse(
            predicted_passenger_count=predicted_count,
            bus_capacity=capacity,
            recommended_buses=recommended_buses
        )

    @staticmethod
    def optimize_fleet(db: Session, request: 'FleetOptimizationRequest') -> 'FleetOptimizationResponse':
        from app.services.optimization_engine import OptimizationEngine
        import logging
        
        logger = logging.getLogger(__name__)
        logger.info("Routing fleet optimization request to unified MILP engine.")
        
        available_buses = request.available_buses if request.available_buses is not None else 1000
        
        return OptimizationEngine.run(
            db=db,
            available_buses=available_buses,
            bus_capacity=request.bus_capacity,
            max_buses_per_route=request.max_buses_per_route if request.max_buses_per_route else 15
        )
