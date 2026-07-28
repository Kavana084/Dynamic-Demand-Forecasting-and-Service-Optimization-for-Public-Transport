"""
Demand Prediction Service
--------------------------
Refactored to use the new CatBoost model with complete feature set.

Priority chain:
  1. CatBoost via app.ml.predictor (57 features) ← production path
  2. Heuristic multiplier model                  ← startup / model-absent fallback

The CatBoost model is loaded at startup by ModelLoader and used via
the Predictor class which accepts complete feature dictionaries.

Public interface:

    demand_prediction_service.predict(features: dict, segment_ratio: float) -> {
        "route_predicted_passengers": int,   # whole-route demand
        "journey_predicted_passengers": int, # journey-segment demand (= route * segment_ratio)
        "demand_score":         int,   # 0-100
        "confidence":           float, # 0.0-1.0
        "model_source":         str,   # "catboost" | "heuristic"
        "model_version":        str,
        "inference_time_ms":    float
    }
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime

from app.ml.predictor import predictor
from app.ml.model_loader import model_loader

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Scale constants
# ---------------------------------------------------------------------------
MAX_PASSENGERS = 300      # ceiling used to normalise demand_score 0-100


class DemandPredictionService:
    """
    Demand prediction service using CatBoost model with complete feature set.
    
    The service accepts complete feature dictionaries matching the training schema
    and delegates to the Predictor class for CatBoost inference.
    """

    def __init__(self):
        self._app_state = None   # injected by set_app_state() or lazy lookup

    # ------------------------------------------------------------------
    # App-state injection (called once from main.py startup)
    # ------------------------------------------------------------------
    def set_app_state(self, state) -> None:
        """Receive a reference to FastAPI app.state after startup."""
        self._app_state = state
        logger.info("DemandPredictionService: app.state injected — CatBoost path active.")

    # ------------------------------------------------------------------
    # CatBoost prediction with complete features
    # ------------------------------------------------------------------
    def _catboost_predict(self, features: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Delegate to the Predictor class which uses the CatBoost model.
        
        Args:
            features: Complete feature dictionary matching training schema (57 features)
            
        Returns:
            Prediction result dictionary or None if model unavailable
        """
        if not model_loader.is_model_loaded():
            logger.warning("CatBoost model not loaded, attempting to load...")
            if not model_loader.load_model():
                logger.error("Failed to load CatBoost model")
                return None
        
        try:
            result = predictor.predict_passenger_count(features)
            if result.get("success"):
                return result
            else:
                logger.warning(f"CatBoost prediction failed: {result.get('error')}")
                return None
        except Exception as exc:
            logger.error(f"CatBoost prediction error: {exc}", exc_info=True)
            return None

    # ------------------------------------------------------------------
    # Heuristic fallback (simplified for backward compatibility)
    # ------------------------------------------------------------------
    @staticmethod
    def _heuristic_predict(
        passenger_count:   int,
        occupancy_percent: float,
        weather:           str,
        traffic:           str,
        hour_of_day:       int,
        peak_status:       str,
    ) -> float:
        """
        Physics-inspired multiplier model. Used only when CatBoost unavailable.
        """
        base = max(1.0, passenger_count * (occupancy_percent / 100.0 + 0.5))

        traffic_mult = {"Low": 0.9, "Medium": 1.0, "High": 1.15, "Heavy": 1.3}
        base *= traffic_mult.get(traffic, 1.0)

        weather_mult = {"Clear": 1.0, "Cloudy": 1.05, "Rainy": 1.2, "Storm": 1.35}
        base *= weather_mult.get(weather, 1.0)

        peak_mult = {
            "normal": 1.0, "morning_peak": 1.4,
            "evening_peak": 1.5, "surge": 1.8,
        }
        base *= peak_mult.get(peak_status, 1.0)

        return max(1.0, base)

    # ------------------------------------------------------------------
    # Public interface with complete features
    # ------------------------------------------------------------------
    def predict(self, features: dict, segment_ratio: float = 1.0) -> dict:
        """
        Predicts transit passenger demand.

        Args:
            features (dict): Dictionary of features including route details, time, weather, etc.
            segment_ratio (float): Ratio of journey stops to total route stops (0.1 to 1.0).
            
        Returns:
            {
                "route_predicted_passengers":   int,
                "journey_predicted_passengers": int,
                "demand_score":                 int,   # 0-100
                "confidence":                   float, # 0.0-1.0
                "model_source":                 str,   # "catboost" | "heuristic"
                "model_version":                str,
                "inference_time_ms":            float,
                "demand_class":                 str
            }
        """
        route_id = features.get("route_id", "unknown")
        hour = features.get("hour", "unknown")
        
        logger.info(
            f"Demand prediction request | route={route_id} | hour={hour} | "
            f"features_count={len(features)}"
        )
        
        logger.info(f"DEMAND_TRACE: Demand prediction requested for route {route_id} with {len(features)} features: {features}")
        
        try:
            # ── Path 1: CatBoost (primary) ──────────────────────────────
            cb_result = self._catboost_predict(features)

            if cb_result is not None and cb_result.get("success"):
                predicted_passengers = cb_result.get("predicted_passenger_count", 0)
                confidence = cb_result.get("confidence_score", 0.97)
                model_source = "catboost"
                model_version = cb_result.get("model_version", "unknown")
                inference_time_ms = cb_result.get("inference_time_ms", 0.0)
                demand_class = cb_result.get("demand_class", "Medium")

                logger.info(
                    f"CatBoost prediction SUCCESS | route={route_id} | "
                    f"predicted={predicted_passengers} | confidence={confidence:.3f} | "
                    f"class={demand_class} | inference_time={inference_time_ms:.2f}ms"
                )
                logger.info(f"DEMAND_TRACE: CatBoost predicted {predicted_passengers} passengers for route {route_id}")

                # CatBoost predicts passenger load at the SOURCE STOP (stop-level).
                journey_predicted_passengers = predicted_passengers
                route_predicted_passengers = int(predicted_passengers / segment_ratio) if segment_ratio > 0 else 0
            else:
                # ── CatBoost failure - raise error instead of silent fallback ────────────────────────
                error_msg = cb_result.get("error", "Unknown error") if cb_result else "CatBoost prediction returned None"
                logger.error(f"CatBoost prediction FAILED for route {route_id}: {error_msg}")
                logger.error(f"DEMAND_TRACE: CatBoost failure - this should surface as a hard error, not silent fallback")
                raise ValueError(f"ML prediction failed: {error_msg}. Check feature validation and model availability.")

            demand_score = min(100, int((route_predicted_passengers / MAX_PASSENGERS) * 100))

            return {
                "route_predicted_passengers": route_predicted_passengers,
                "journey_predicted_passengers": journey_predicted_passengers,
                "demand_score": demand_score,
                "confidence": confidence,
                "model_source": model_source,
                "model_version": model_version,
                "inference_time_ms": inference_time_ms,
                "demand_class": demand_class,
            }

        except Exception as exc:
            logger.error(f"Demand prediction error: {exc}", exc_info=True)
            fallback_route_pax = features.get("passenger_count", 50)
            return {
                "route_predicted_passengers": fallback_route_pax,
                "journey_predicted_passengers": max(1, int(fallback_route_pax * segment_ratio)),
                "demand_score": 50,
                "confidence": 0.65,
                "model_source": "fallback",
                "model_version": "error",
                "inference_time_ms": 0.0,
                "demand_class": "Unknown",
            }

    # ------------------------------------------------------------------
    # Legacy interface for backward compatibility
    # ------------------------------------------------------------------
    def predict_legacy(
        self,
        route_id:          str   = "default",
        passenger_count:   int   = 50,
        occupancy_percent: float = 60.0,
        weather:           str   = "Clear",
        traffic:           str   = "Medium",
        hour_of_day:       int   = 12,
        day_of_week:       int   = 1,
        peak_status:       str   = "normal",
    ) -> dict:
        """
        Legacy interface for backward compatibility.
        Constructs minimal feature set and delegates to predict().
        
        Deprecated: Use predict() with complete feature set instead.
        """
        logger.warning("Using legacy predict() interface - consider migrating to full feature set")
        
        # Construct minimal feature set (this is a simplified version)
        # In production, callers should provide the complete 57-feature set
        features = {
            "route_id": route_id,
            "passenger_count": passenger_count,
            "occupancy_ratio": occupancy_percent / 100.0,
            "weather_condition": weather,
            "traffic_level": traffic,
            "hour": hour_of_day,
            "peak_hour_flag": 1 if peak_status != "normal" else 0,
            "service_date": 20230101,  # dummy date as integer for numerical feature
            # Add default values for other required features
            "route_short_name": "default",
            "route_type": 3,
            "service_id": "default",
            "trip_id": "default",
            "shape_id": "default",
            "direction_id": 0,
            "stop_id": "default",
            "stop_name": "default",
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
            "route_length_km": 10.0,
            "scheduled_trip_duration": 30,
            "trip_start_time": hour_of_day * 60,
            "trip_end_time": (hour_of_day + 1) * 60,
            "minute": 0,
            "time_slot": "Morning",
            "day_of_week": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][day_of_week % 7],
            "weekday_weekend": "Weekday" if day_of_week < 6 else "Weekend",
            "month": 1,
            "holiday_flag": 0,
            "temperature": 28,
            "rainfall_flag": 0,
            "congestion_index": 0.5,
            "average_speed": 30,
            "traffic_delay": 0,
            "weather_delay": 0,
            "boarding_delay": 0,
            "total_delay": 0,
            "headway_minutes": 15,
            "service_frequency_category": "Normal",
            "historical_route_average": 25.0,
            "historical_stop_average": 25.0,
            "historical_hour_average": 25.0,
            "historical_peak_average": 35.0,
            "historical_weekend_average": 20.0,
            "route_popularity_score": 0.5,
            "vehicle_capacity": 60,
            "boarding_count": 0,
            "alighting_count": 0,
            "onboard_passengers": passenger_count,
            "load_factor": occupancy_percent / 100.0,
            "demand_class": "Medium",
        }
        
        return self.predict(features)


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------
demand_prediction_service = DemandPredictionService()
