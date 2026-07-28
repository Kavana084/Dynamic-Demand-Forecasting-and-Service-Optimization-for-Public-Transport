import pandas as pd
import numpy as np
import time
from typing import Dict, Any, List, Optional
from datetime import datetime
from app.ml.model_loader import model_loader
from app.database.connection import SessionLocal
from app.database.models import ForecastHistory
import logging

logger = logging.getLogger(__name__)

class Predictor:
    """CatBoost predictor for passenger demand forecasting."""

    @staticmethod
    def _validate_features(features: Dict[str, Any], expected_features: List[str]) -> List[str]:
        """
        Validate features against expected training schema.
        
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Check for missing features
        missing_features = set(expected_features) - set(features.keys())
        if missing_features:
            errors.append(f"Missing features: {sorted(missing_features)}")
        
        # Check for extra features (warning only)
        extra_features = set(features.keys()) - set(expected_features)
        if extra_features:
            logger.warning(f"Extra features provided (will be ignored): {sorted(extra_features)}")
        
        return errors

    @staticmethod
    def _construct_feature_dataframe(
        features: Dict[str, Any],
        expected_features: List[str],
        categorical_features: List[str]
    ) -> pd.DataFrame:
        """
        Construct DataFrame with exact feature order and proper types.
        
        Args:
            features: Input feature dictionary
            expected_features: Expected feature names in order
            categorical_features: Categorical feature names
            
        Returns:
            DataFrame ready for CatBoost prediction
        """
        # Create DataFrame with expected feature order
        feature_data = {}
        for feat in expected_features:
            if feat in features:
                feature_data[feat] = [features[feat]]
            else:
                # Fill missing features with default values
                feature_data[feat] = [0]  # Default for numeric
                logger.warning(f"Feature '{feat}' missing, using default value 0")
        
        df = pd.DataFrame(feature_data)
        
        # Convert categorical features to strings
        for cat_feat in categorical_features:
            if cat_feat in df.columns:
                df[cat_feat] = df[cat_feat].astype(str)
        
        return df

    @staticmethod
    def _calculate_demand_class(passenger_count: int, vehicle_capacity: int = 60) -> str:
        """Calculate demand class based on passenger count and capacity."""
        if vehicle_capacity <= 0:
            vehicle_capacity = 60
        
        load_factor = passenger_count / vehicle_capacity
        
        if load_factor < 0.3:
            return "Low"
        elif load_factor < 0.6:
            return "Medium"
        elif load_factor < 0.9:
            return "High"
        else:
            return "Very High"

    @staticmethod
    def _estimate_confidence(model_metrics: Dict[str, Any]) -> float:
        """Estimate confidence based on model metrics."""
        # Base confidence from R² score
        r2 = model_metrics.get('R2', 0.97)
        base_confidence = min(0.99, max(0.70, r2))
        
        # Adjust based on RMSE (lower RMSE = higher confidence)
        rmse = model_metrics.get('RMSE', 3.0)
        if rmse < 2.0:
            base_confidence += 0.02
        elif rmse > 5.0:
            base_confidence -= 0.05
        
        return round(min(0.99, max(0.60, base_confidence)), 3)

    @staticmethod
    def _log_prediction(
        route_id: str,
        trip_id: str,
        stop_id: str,
        predicted_passengers: int,
        confidence_score: float,
        model_version: str,
        target_timestamp: Optional[datetime] = None
    ) -> None:
        """
        Log prediction to database tables (forecast_history only).
        
        Args:
            route_id: Route identifier
            trip_id: Trip identifier
            stop_id: Stop identifier
            predicted_passengers: Predicted passenger count
            confidence_score: Confidence score (0-1)
            model_version: Model version identifier
            target_timestamp: Target timestamp for the forecast (default: now)
        """
        db = SessionLocal()
        try:
            current_time = datetime.utcnow()
            if target_timestamp is None:
                target_timestamp = current_time
            
            # Log to forecast_history table
            forecast_record = ForecastHistory(
                generated_at=current_time,
                target_timestamp=target_timestamp,
                route_id=route_id,
                predicted_passengers=predicted_passengers,
                confidence_score=confidence_score,
                model_version=model_version
            )
            db.add(forecast_record)
            
            db.commit()
            logger.debug(
                f"Prediction logged: route={route_id}, trip={trip_id}, stop={stop_id}, "
                f"predicted={predicted_passengers}, confidence={confidence_score:.3f}"
            )
            
        except Exception as e:
            logger.error(f"Failed to log prediction to database: {e}", exc_info=True)
            db.rollback()
        finally:
            db.close()

    @staticmethod
    def predict_passenger_count(features: Dict[str, Any]) -> Dict[str, Any]:
        """
        Predict passenger count using CatBoost model with complete feature set.
        
        Args:
            features: Complete feature dictionary matching training schema (57 features)
            
        Returns:
            Dictionary containing:
                - predicted_passenger_count: int
                - confidence_score: float
                - demand_class: str
                - inference_time_ms: float
                - model_version: str
                - model_source: str
        """
        start_time = time.time()
        route_id = features.get('route_id', 'unknown')
        
        logger.info("=" * 80)
        logger.info("PREDICTOR DIAGNOSTICS")
        logger.info("=" * 80)
        logger.info(f"Predictor.predict called | route={route_id} | features={len(features)}")
        
        # Get model and metadata
        model = model_loader.get_model()
        if model is None:
            logger.error(f"✗ Model is not loaded for route {route_id}. Cannot make prediction.")
            logger.info("=" * 80)
            return {
                "success": False,
                "error": "ML model is not available",
                "predicted_passenger_count": None,
                "confidence_score": 0.0,
                "demand_class": "Unknown",
                "inference_time_ms": 0.0,
                "model_version": None,
                "model_source": "error"
            }
        
        logger.info(f"✓ Model loaded successfully")
        
        expected_features = model_loader.get_feature_names()
        if not expected_features and hasattr(model, 'feature_names_'):
            expected_features = list(model.feature_names_)

        categorical_features = model_loader.get_categorical_features()
        if not categorical_features:
            # Fallback based on DataPreprocessor schema
            categorical_features = [
                'route_id', 'route_short_name', 'service_id', 'trip_id', 'shape_id',
                'stop_id', 'stop_name', 'time_slot', 'day_of_week', 'weekday_weekend',
                'weather_condition', 'traffic_level', 'service_frequency_category', 'area_type'
            ]
            
        model_metrics = model_loader.get_training_metrics()
        model_config = model_loader.get_model_config()
        
        logger.info(f"Expected features: {len(expected_features)}")
        logger.info(f"Categorical features: {len(categorical_features)}")
        logger.info(f"Provided features: {len(features)}")
        
        # Validate features
        validation_errors = Predictor._validate_features(features, expected_features)
        if validation_errors:
            error_msg = "; ".join(validation_errors)
            logger.error(f"✗ Feature validation failed for route {route_id}: {error_msg}")
            logger.info("=" * 80)
            return {
                "success": False,
                "error": error_msg,
                "predicted_passenger_count": None,
                "confidence_score": 0.0,
                "demand_class": "Unknown",
                "inference_time_ms": 0.0,
                "model_version": model_config.get('training_date', 'unknown'),
                "model_source": "validation_error"
            }
        
        logger.info(f"✓ Feature validation passed for route {route_id}")
        
        try:
            # Construct DataFrame with exact feature order
            logger.info("Constructing feature DataFrame...")
            df = Predictor._construct_feature_dataframe(
                features, expected_features, categorical_features
            )
            logger.info(f"✓ DataFrame constructed: shape={df.shape}")
            
            # Make prediction
            logger.info("Making CatBoost prediction...")
            prediction = model.predict(df)[0]
            passenger_count = max(0, int(round(prediction)))
            
            logger.info(f"✓ Raw model prediction for route {route_id}: {prediction:.2f}")
            logger.info(f"✓ Rounded prediction: {passenger_count} passengers")
            
            # Calculate derived metrics
            vehicle_capacity = features.get('vehicle_capacity', 60)
            demand_class = Predictor._calculate_demand_class(passenger_count, vehicle_capacity)
            confidence_score = Predictor._estimate_confidence(model_metrics)
            
            inference_time_ms = (time.time() - start_time) * 1000
            
            logger.info(f"✓ Derived metrics:")
            logger.info(f"  Vehicle capacity: {vehicle_capacity}")
            logger.info(f"  Demand class: {demand_class}")
            logger.info(f"  Confidence score: {confidence_score:.3f}")
            logger.info(f"  Inference time: {inference_time_ms:.2f}ms")
            
            logger.info(f"✓ Prediction SUCCESS for route {route_id}: {passenger_count} passengers")
            
            # Log prediction to database (non-critical)
            try:
                Predictor._log_prediction(
                    route_id=features.get('route_id', 'unknown'),
                    trip_id=features.get('trip_id', 'unknown'),
                    stop_id=features.get('stop_id', 'unknown'),
                    predicted_passengers=passenger_count,
                    confidence_score=confidence_score,
                    model_version=model_config.get('training_date', 'unknown'),
                    target_timestamp=None
                )
                logger.info("✓ Prediction logged to database")
            except Exception as e:
                # Database logging is non-critical - log warning and continue
                logger.warning(f"✗ Prediction logging skipped (non-critical): {e}")
            
            logger.info("=" * 80)
            return {
                "success": True,
                "predicted_passenger_count": passenger_count,
                "confidence_score": confidence_score,
                "demand_class": demand_class,
                "inference_time_ms": round(inference_time_ms, 2),
                "model_version": model_config.get('training_date', 'unknown'),
                "model_source": "catboost",
                "error": None
            }
            
        except Exception as e:
            inference_time_ms = (time.time() - start_time) * 1000
            logger.error(f"✗ Prediction failed: {e}", exc_info=True)
            logger.info("=" * 80)
            return {
                "success": False,
                "error": str(e),
                "predicted_passenger_count": None,
                "confidence_score": 0.0,
                "demand_class": "Unknown",
                "inference_time_ms": round(inference_time_ms, 2),
                "model_version": model_config.get('training_date', 'unknown'),
                "model_source": "error"
            }

    @staticmethod
    def predict_batch(features_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Predict passenger counts for multiple feature sets.
        
        Args:
            features_list: List of feature dictionaries
            
        Returns:
            List of prediction dictionaries
        """
        results = []
        for features in features_list:
            result = Predictor.predict_passenger_count(features)
            results.append(result)
        
        logger.info(f"Batch prediction completed: {len(results)} predictions")
        return results


predictor = Predictor()