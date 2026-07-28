import os
import logging
from typing import Dict, Any
from fastapi import HTTPException

from app.ml.model_loader import model_loader
from app.ml.predictor import predictor

logger = logging.getLogger(__name__)

class PredictionService:
    """
    Prediction service using the new CatBoost model with complete feature set.

    This service is a thin wrapper around the ModelLoader and Predictor classes,
    providing backward compatibility for existing API endpoints.

    NOTE: ``self.model`` is a *property* that delegates to model_loader.get_model().
    It was previously a plain ``None`` attribute that was never assigned, causing
    the ``svc.model is None`` guard in api_routes.py to always fire a 503 even when
    CatBoost had loaded successfully.  The property preserves the public interface
    while correctly reflecting live model state.
    """

    @property
    def model(self):
        """Return the live CatBoost model (or None if not yet loaded)."""
        return model_loader.get_model()

    def init(self, model_path: str = None):
        """
        Initialize the service by loading the CatBoost model.

        Args:
            model_path: Path to the CatBoost model file (.cbm) - deprecated, not used
        """
        logger.info("Initializing PredictionService with CatBoost model...")
        success = model_loader.load_model()
        if success:
            logger.info("PredictionService initialized successfully")
        else:
            logger.error("Failed to initialize PredictionService")
        
    def predict_demand(self, route_id: str, hour: int, weather_condition: str, traffic: str) -> int:
        """
        Predict passenger demand for a specific route based on high-level inputs.
        
        This method constructs a complete feature dictionary from the limited inputs
        and delegates to the CatBoost predictor.
        
        Args:
            route_id: Route identifier
            hour: Hour of day (0-23)
            weather_condition: Weather condition (e.g., "Clear", "Rainy")
            traffic: Traffic level (e.g., "Low", "Medium", "High")
            
        Returns:
            Predicted passenger count (int)
        """
        if not model_loader.is_model_loaded():
            logger.error("Model not loaded in PredictionService")
            raise HTTPException(status_code=503, detail="Model not initialized")
        
        # Construct complete feature dictionary from limited inputs
        # This is a simplified version - in production, callers should provide full features
        features = self._construct_features_from_inputs(
            route_id=route_id,
            hour=hour,
            weather_condition=weather_condition,
            traffic=traffic
        )
        
        # Delegate to predictor
        result = predictor.predict_passenger_count(features)
        
        if not result.get("success"):
            logger.error(f"Prediction failed: {result.get('error')}")
            raise HTTPException(status_code=500, detail=f"Prediction failed: {result.get('error')}")
        
        predicted_passengers = result.get("predicted_passenger_count")
        if predicted_passengers is None:
            raise HTTPException(status_code=500, detail="Model returned no prediction")
            
        # Enforce safety bounds
        demand = max(0, int(predicted_passengers))
        
        return demand
    
    def _construct_features_from_inputs(
        self, route_id: str, hour: int, weather_condition: str, traffic: str
    ) -> Dict[str, Any]:
        """
        Construct a complete feature dictionary from limited high-level inputs.
        
        This method fills missing features with reasonable defaults.
        In production, callers should provide the complete 57-feature set.
        """
        # Determine time slot
        if 5 <= hour < 12:
            time_slot = "Morning"
        elif 12 <= hour < 17:
            time_slot = "Afternoon"
        elif 17 <= hour < 21:
            time_slot = "Evening"
        else:
            time_slot = "Night"
        
        # Determine peak hour flag
        peak_hour_flag = 1 if (8 <= hour <= 10 or 17 <= hour <= 20) else 0
        
        # Determine congestion index from traffic
        traffic_lower = traffic.lower()
        if traffic_lower == 'high' or traffic_lower == 'heavy':
            congestion_index = 1.5
        elif traffic_lower == 'medium':
            congestion_index = 1.2
        else:
            congestion_index = 1.0
        
        # Map traffic to traffic_level
        traffic_level_map = {
            'low': 'Low',
            'medium': 'Medium',
            'high': 'High',
            'heavy': 'Heavy'
        }
        traffic_level = traffic_level_map.get(traffic_lower, 'Medium')
        
        # Construct complete feature set
        features = {
            # Route features
            "route_id": route_id,
            "route_short_name": route_id,
            "route_type": 3,
            "service_id": "default",
            "trip_id": f"{route_id}_{hour}",
            "shape_id": "default",
            "direction_id": 0,
            
            # Stop features
            "stop_id": route_id,  # Use route_id for route-level prediction
            "stop_name": f"Stop_{route_id}",
            "stop_sequence": 1,
            "stop_lat": 0.0,
            "stop_lon": 0.0,
            "terminal_stop_flag": 0,
            "major_interchange_flag": 0,
            "area_type": "Mixed",
            "cumulative_distance": 0.0,
            "remaining_distance": 0.0,
            "number_of_stops": 10,
            "remaining_stops": 5,
            
            # Trip features
            "route_length_km": 10.0,
            "scheduled_trip_duration": 30,
            "trip_start_time": hour * 60,
            "trip_end_time": (hour + 1) * 60,
            
            # Temporal features
            "hour": hour,
            "minute": 0,
            "time_slot": time_slot,
            "day_of_week": "Monday",
            "weekday_weekend": "Weekday",
            "month": 1,
            "holiday_flag": 0,
            "peak_hour_flag": peak_hour_flag,
            
            # Weather features
            "weather_condition": weather_condition,
            "temperature": 28,
            "rainfall_flag": 0,
            
            # Service features
            "headway_minutes": 15,
            "service_frequency_category": "Normal",
            
            # Historical features (defaults)
            "historical_route_average": 25.0,
            "historical_stop_average": 25.0,
            "historical_hour_average": 25.0,
            "historical_peak_average": 35.0,
            "historical_weekend_average": 20.0,
            
            # Operational features
            "route_popularity_score": 0.5,
            "vehicle_capacity": 60,
        }
        
        return features


# Singleton instance initialized immediately
prediction_service = PredictionService()

def init_service(model_path: str = None):
    """
    Initialize the prediction service with the CatBoost model.
    
    Args:
        model_path: Path to the CatBoost model file (.cbm) - deprecated, not used
    """
    prediction_service.init(model_path)
    return prediction_service
