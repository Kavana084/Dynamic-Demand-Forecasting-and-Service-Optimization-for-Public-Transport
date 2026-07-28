"""
Real-time Feature Engineering and Inference Module
Uses trained CatBoost model for passenger demand prediction.
"""

import os
import pandas as pd
import numpy as np
from catboost import CatBoostRegressor
from typing import Dict, List, Any, Optional
import logging
from datetime import datetime

from config import config
from data_preprocessing import DataPreprocessor

logger = logging.getLogger(__name__)


class RealTimePredictor:
    """Real-time passenger demand prediction using trained CatBoost model."""
    
    def __init__(self, model_path: str = None):
        """
        Initialize the predictor with a trained model.
        
        Args:
            model_path: Path to the trained CatBoost model file
        """
        self.model = None
        self.model_path = model_path or config.get('model_load_path')
        self.preprocessor = DataPreprocessor()
        self.feature_names = None
        self.categorical_features = None
        self.model_loaded = False
        
        # Load model on initialization
        self.load_model()
    
    def load_model(self) -> bool:
        """
        Load the trained CatBoost model.
        
        Returns:
            True if model loaded successfully, False otherwise
        """
        try:
            if not os.path.exists(self.model_path):
                logger.error(f"Model file not found at {self.model_path}")
                return False
            
            logger.info(f"Loading model from {self.model_path}")
            self.model = CatBoostRegressor()
            self.model.load_model(self.model_path)
            
            # Load model config to get feature names
            config_path = os.path.join(config.get('output_dir'), 'model_config.json')
            if os.path.exists(config_path):
                import json
                with open(config_path, 'r') as f:
                    model_config = json.load(f)
                self.feature_names = model_config.get('feature_names', [])
                self.categorical_features = model_config.get('categorical_features', [])
                logger.info(f"Loaded feature names: {len(self.feature_names)} features")
                logger.info(f"Loaded categorical features: {len(self.categorical_features)} features")
            else:
                logger.warning("Model config not found, using preprocessor defaults")
                self.feature_names = self.preprocessor.get_feature_names()
                self.categorical_features = self.preprocessor.get_categorical_features()
            
            self.model_loaded = True
            logger.info("Model loaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load model: {e}", exc_info=True)
            self.model_loaded = False
            return False
    
    def construct_feature_vector(
        self,
        trip_data: Dict[str, Any],
        weather_data: Dict[str, Any],
        current_time: datetime
    ) -> Dict[str, Any]:
        """
        Construct a feature vector matching the training schema.
        
        Args:
            trip_data: Dictionary containing trip information (route_id, stop_id, etc.)
            weather_data: Dictionary containing weather information
            current_time: Current datetime
            
        Returns:
            Dictionary of features matching training schema
        """
        features = {}
        
        # Route Features
        features['route_id'] = str(trip_data.get('route_id', ''))
        features['route_short_name'] = str(trip_data.get('route_short_name', ''))
        features['route_type'] = int(trip_data.get('route_type', 3))  # Default to bus
        features['service_id'] = str(trip_data.get('service_id', ''))
        features['trip_id'] = str(trip_data.get('trip_id', ''))
        features['shape_id'] = str(trip_data.get('shape_id', ''))
        features['direction_id'] = int(trip_data.get('direction_id', 0))
        
        # Stop Features
        features['stop_id'] = str(trip_data.get('stop_id', ''))
        features['stop_name'] = str(trip_data.get('stop_name', ''))
        features['stop_sequence'] = int(trip_data.get('stop_sequence', 0))
        features['stop_lat'] = float(trip_data.get('stop_lat', 0.0))
        features['stop_lon'] = float(trip_data.get('stop_lon', 0.0))
        features['terminal_stop_flag'] = int(trip_data.get('terminal_stop_flag', 0))
        features['major_interchange_flag'] = int(trip_data.get('major_interchange_flag', 0))
        features['area_type'] = str(trip_data.get('area_type', 'Mixed'))
        
        # Calculate distance features (simplified for real-time)
        features['cumulative_distance'] = float(trip_data.get('cumulative_distance', 0.0))
        features['remaining_distance'] = float(trip_data.get('remaining_distance', 0.0))
        features['number_of_stops'] = int(trip_data.get('number_of_stops', 10))
        features['remaining_stops'] = int(trip_data.get('remaining_stops', 5))
        
        # Trip Features
        features['route_length_km'] = float(trip_data.get('route_length_km', 10.0))
        features['scheduled_trip_duration'] = int(trip_data.get('scheduled_trip_duration', 30))
        features['trip_start_time'] = int(current_time.hour * 60 + current_time.minute)
        features['trip_end_time'] = features['trip_start_time'] + features['scheduled_trip_duration']
        
        # Temporal Features
        features['hour'] = current_time.hour
        features['minute'] = current_time.minute
        features['time_slot'] = self._get_time_slot(current_time.hour)
        features['day_of_week'] = current_time.strftime('%A')
        features['weekday_weekend'] = 'Weekday' if current_time.weekday() < 5 else 'Weekend'
        features['month'] = current_time.month
        features['holiday_flag'] = int(self._is_holiday(current_time))
        features['peak_hour_flag'] = int(self._is_peak_hour(current_time.hour))
        
        # Weather Features
        features['weather_condition'] = str(weather_data.get('condition', 'Sunny'))
        features['temperature'] = int(weather_data.get('temperature', 28))
        features['rainfall_flag'] = int(weather_data.get('rainfall', 0) > 0)
        
        # Traffic Features (estimate based on time and weather)
        features['congestion_index'] = self._estimate_congestion(current_time.hour, weather_data.get('rainfall', 0))
        features['traffic_level'] = self._get_traffic_level(features['congestion_index'])
        features['average_speed'] = self._estimate_speed(features['congestion_index'], features['weather_condition'])
        features['traffic_delay'] = int(features['congestion_index'] * 10)
        features['weather_delay'] = int(features['rainfall_flag'] * 5)
        features['boarding_delay'] = np.random.randint(0, 3)
        features['total_delay'] = features['traffic_delay'] + features['weather_delay'] + features['boarding_delay']
        
        # Service Features
        features['headway_minutes'] = int(trip_data.get('headway_minutes', 15))
        features['service_frequency_category'] = self._get_frequency_category(features['headway_minutes'])
        
        # Historical Features (use defaults for real-time)
        features['historical_route_average'] = float(trip_data.get('historical_route_average', 25.0))
        features['historical_stop_average'] = float(trip_data.get('historical_stop_average', 25.0))
        features['historical_hour_average'] = float(trip_data.get('historical_hour_average', 25.0))
        features['historical_peak_average'] = float(trip_data.get('historical_peak_average', 35.0))
        features['historical_weekend_average'] = float(trip_data.get('historical_weekend_average', 20.0))
        
        # Operational Features
        features['route_popularity_score'] = float(trip_data.get('route_popularity_score', 0.5))
        features['vehicle_capacity'] = int(trip_data.get('vehicle_capacity', 60))
        
        return features
    
    def predict(
        self,
        trip_data: Dict[str, Any],
        weather_data: Dict[str, Any],
        current_time: datetime = None
    ) -> Dict[str, Any]:
        """
        Predict passenger count for a trip-stop event.
        
        Args:
            trip_data: Dictionary containing trip information
            weather_data: Dictionary containing weather information
            current_time: Current datetime (defaults to now)
            
        Returns:
            Dictionary containing prediction and metadata
        """
        if current_time is None:
            current_time = datetime.now()
        
        if not self.model_loaded:
            logger.error("Model not loaded, cannot make predictions")
            return {
                'success': False,
                'error': 'Model not loaded',
                'passenger_count': None
            }
        
        try:
            # Construct feature vector
            features = self.construct_feature_vector(trip_data, weather_data, current_time)
            
            # Create DataFrame with correct feature order
            feature_df = pd.DataFrame([features])
            
            # Ensure all required features are present
            missing_features = set(self.feature_names) - set(feature_df.columns)
            if missing_features:
                logger.warning(f"Missing features: {missing_features}")
                for feat in missing_features:
                    feature_df[feat] = 0  # Default value
            
            # Reorder columns to match training
            feature_df = feature_df[self.feature_names]
            
            # Convert categorical features to string
            for col in self.categorical_features:
                if col in feature_df.columns:
                    feature_df[col] = feature_df[col].astype(str)
            
            # Make prediction
            passenger_count = self.model.predict(feature_df)[0]
            passenger_count = max(0, int(round(passenger_count)))
            
            # Calculate derived operational features
            vehicle_capacity = features['vehicle_capacity']
            occupancy_ratio = passenger_count / vehicle_capacity
            load_factor = min(occupancy_ratio, 1.5)
            
            if load_factor < 0.3:
                demand_class = 'Low'
            elif load_factor < 0.6:
                demand_class = 'Medium'
            elif load_factor < 0.9:
                demand_class = 'High'
            else:
                demand_class = 'Very High'
            
            logger.info(f"Prediction successful: {passenger_count} passengers")
            
            return {
                'success': True,
                'passenger_count': passenger_count,
                'occupancy_ratio': round(occupancy_ratio, 3),
                'load_factor': round(load_factor, 3),
                'demand_class': demand_class,
                'prediction_time': current_time.isoformat(),
                'features_used': self.feature_names
            }
            
        except Exception as e:
            logger.error(f"Prediction failed: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'passenger_count': None
            }
    
    def predict_batch(
        self,
        trips_data: List[Dict[str, Any]],
        weather_data: Dict[str, Any],
        current_time: datetime = None
    ) -> List[Dict[str, Any]]:
        """
        Predict passenger counts for multiple trip-stop events.
        
        Args:
            trips_data: List of trip data dictionaries
            weather_data: Dictionary containing weather information
            current_time: Current datetime (defaults to now)
            
        Returns:
            List of prediction dictionaries
        """
        if current_time is None:
            current_time = datetime.now()
        
        if not self.model_loaded:
            logger.error("Model not loaded, cannot make predictions")
            return [{'success': False, 'error': 'Model not loaded'}] * len(trips_data)
        
        try:
            # Construct feature vectors for all trips
            features_list = [
                self.construct_feature_vector(trip, weather_data, current_time)
                for trip in trips_data
            ]
            
            # Create DataFrame
            feature_df = pd.DataFrame(features_list)
            
            # Ensure all required features are present
            missing_features = set(self.feature_names) - set(feature_df.columns)
            if missing_features:
                logger.warning(f"Missing features: {missing_features}")
                for feat in missing_features:
                    feature_df[feat] = 0
            
            # Reorder columns
            feature_df = feature_df[self.feature_names]
            
            # Convert categorical features
            for col in self.categorical_features:
                if col in feature_df.columns:
                    feature_df[col] = feature_df[col].astype(str)
            
            # Make predictions
            predictions = self.model.predict(feature_df)
            predictions = np.maximum(0, np.round(predictions)).astype(int)
            
            # Create result dictionaries
            results = []
            for i, (trip, pred) in enumerate(zip(trips_data, predictions)):
                vehicle_capacity = trip.get('vehicle_capacity', 60)
                occupancy_ratio = pred / vehicle_capacity
                load_factor = min(occupancy_ratio, 1.5)
                
                if load_factor < 0.3:
                    demand_class = 'Low'
                elif load_factor < 0.6:
                    demand_class = 'Medium'
                elif load_factor < 0.9:
                    demand_class = 'High'
                else:
                    demand_class = 'Very High'
                
                results.append({
                    'success': True,
                    'trip_id': trip.get('trip_id', ''),
                    'stop_id': trip.get('stop_id', ''),
                    'passenger_count': int(pred),
                    'occupancy_ratio': round(occupancy_ratio, 3),
                    'load_factor': round(load_factor, 3),
                    'demand_class': demand_class,
                    'prediction_time': current_time.isoformat()
                })
            
            logger.info(f"Batch prediction successful: {len(results)} predictions")
            return results
            
        except Exception as e:
            logger.error(f"Batch prediction failed: {e}", exc_info=True)
            return [{'success': False, 'error': str(e)}] * len(trips_data)
    
    # Helper methods
    def _get_time_slot(self, hour: int) -> str:
        """Get time slot category from hour."""
        if 0 <= hour < 6:
            return 'Early Morning'
        elif 6 <= hour < 10:
            return 'Morning Peak'
        elif 10 <= hour < 12:
            return 'Morning'
        elif 12 <= hour < 17:
            return 'Afternoon'
        elif 17 <= hour < 20:
            return 'Evening Peak'
        elif 20 <= hour < 23:
            return 'Night'
        else:
            return 'Late Night'
    
    def _is_peak_hour(self, hour: int) -> bool:
        """Check if hour is peak hour."""
        return (7 <= hour < 10) or (17 <= hour < 20)
    
    def _is_holiday(self, date: datetime) -> bool:
        """Check if date is a holiday (simplified)."""
        # Simplified holiday detection
        month = date.month
        day = date.day
        holidays = [(1, 1), (1, 26), (8, 15), (10, 2), (12, 25)]
        return (month, day) in holidays
    
    def _estimate_congestion(self, hour: int, rainfall: float) -> float:
        """Estimate congestion index based on time and weather."""
        base_congestion = 0.3
        
        if self._is_peak_hour(hour):
            base_congestion = 0.7
        elif 11 <= hour < 17:
            base_congestion = 0.5
        
        # Increase congestion with rainfall
        if rainfall > 0:
            base_congestion += 0.2
        
        return min(0.9, base_congestion)
    
    def _get_traffic_level(self, congestion_index: float) -> str:
        """Get traffic level from congestion index."""
        if congestion_index < 0.3:
            return 'Low'
        elif congestion_index < 0.5:
            return 'Medium'
        elif congestion_index < 0.7:
            return 'High'
        else:
            return 'Severe'
    
    def _estimate_speed(self, congestion_index: float, weather: str) -> int:
        """Estimate average speed based on congestion and weather."""
        base_speed = 30
        
        if congestion_index < 0.3:
            base_speed = 40
        elif congestion_index < 0.5:
            base_speed = 30
        elif congestion_index < 0.7:
            base_speed = 20
        else:
            base_speed = 12
        
        if weather in ['Heavy Rain', 'Thunderstorm']:
            base_speed *= 0.7
        elif weather == 'Fog':
            base_speed *= 0.8
        elif weather == 'Light Rain':
            base_speed *= 0.9
        
        return max(5, min(60, int(base_speed)))
    
    def _get_frequency_category(self, headway: int) -> str:
        """Get service frequency category from headway."""
        if headway <= 5:
            return 'Very Frequent'
        elif headway <= 10:
            return 'Frequent'
        elif headway <= 20:
            return 'Normal'
        else:
            return 'Sparse'


# Singleton instance for easy access
_predictor_instance = None


def get_predictor(model_path: str = None) -> RealTimePredictor:
    """
    Get or create a singleton predictor instance.
    
    Args:
        model_path: Optional path to model file
        
    Returns:
        RealTimePredictor instance
    """
    global _predictor_instance
    
    if _predictor_instance is None or (model_path and model_path != _predictor_instance.model_path):
        _predictor_instance = RealTimePredictor(model_path)
    
    return _predictor_instance
