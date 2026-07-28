"""
Data Preprocessing Module for CatBoost Demand Forecasting
Validates schema, converts data types, identifies categorical columns, and prepares data for CatBoost.
"""

import pandas as pd
import numpy as np
from typing import Tuple, List, Dict, Any
import logging
from config import config

logger = logging.getLogger(__name__)


class DataPreprocessor:
    """Preprocesses data for CatBoost training and inference."""
    
    # Expected schema from synthetic_passenger_demand.csv
    # NOTE: Leakage features removed: boarding_count, alighting_count, onboard_passengers, occupancy_ratio, load_factor, demand_class
    EXPECTED_SCHEMA = {
        # Route Features
        'service_date': 'datetime64[ns]',
        'route_id': 'object',
        'route_short_name': 'object',
        'route_type': 'int64',
        'service_id': 'object',
        'trip_id': 'object',
        'shape_id': 'object',
        'direction_id': 'int64',
        
        # Stop Features
        'stop_id': 'object',
        'stop_name': 'object',
        'stop_sequence': 'int64',
        'stop_lat': 'float64',
        'stop_lon': 'float64',
        'terminal_stop_flag': 'int64',
        'major_interchange_flag': 'int64',
        'area_type': 'object',
        'cumulative_distance': 'float64',
        'remaining_distance': 'float64',
        'number_of_stops': 'int64',
        'remaining_stops': 'int64',
        
        # Trip Features
        'route_length_km': 'float64',
        'scheduled_trip_duration': 'int64',
        'trip_start_time': 'int64',
        'trip_end_time': 'int64',
        
        # Temporal Features
        'hour': 'int64',
        'minute': 'int64',
        'time_slot': 'object',
        'day_of_week': 'object',
        'weekday_weekend': 'object',
        'month': 'int64',
        'holiday_flag': 'int64',
        'peak_hour_flag': 'int64',
        
        # Weather Features
        'weather_condition': 'object',
        'temperature': 'int64',
        'rainfall_flag': 'int64',
        
        # Traffic Features
        'congestion_index': 'float64',
        'traffic_level': 'object',
        'average_speed': 'int64',
        'traffic_delay': 'int64',
        'weather_delay': 'int64',
        'boarding_delay': 'int64',
        'total_delay': 'int64',
        
        # Service Features
        'headway_minutes': 'int64',
        'service_frequency_category': 'object',
        
        # Historical Features
        'historical_route_average': 'float64',
        'historical_stop_average': 'float64',
        'historical_hour_average': 'float64',
        'historical_peak_average': 'float64',
        'historical_weekend_average': 'float64',
        
        # Operational Features (clean - no leakage)
        'route_popularity_score': 'float64',
        'vehicle_capacity': 'int64',
        
        # Target Variable
        'passenger_count': 'int64'
    }
    
    # Categorical features (manually defined for consistency)
    # NOTE: demand_class removed due to leakage (derived from passenger counts)
    CATEGORICAL_FEATURES = [
        'route_id',
        'route_short_name',
        'service_id',
        'trip_id',
        'shape_id',
        'stop_id',
        'stop_name',
        'time_slot',
        'day_of_week',
        'weekday_weekend',
        'weather_condition',
        'traffic_level',
        'service_frequency_category',
        'area_type'
    ]
    
    # Numeric columns that should NEVER be categorical
    # NOTE: Leakage features removed: boarding_count, alighting_count, onboard_passengers, occupancy_ratio, load_factor
    NUMERIC_COLUMNS = {
        'route_type', 'direction_id', 'stop_sequence', 'stop_lat', 'stop_lon',
        'terminal_stop_flag', 'major_interchange_flag', 'cumulative_distance',
        'remaining_distance', 'number_of_stops', 'remaining_stops',
        'route_length_km', 'scheduled_trip_duration', 'trip_start_time',
        'trip_end_time', 'hour', 'minute', 'month', 'holiday_flag',
        'peak_hour_flag', 'temperature', 'rainfall_flag', 'congestion_index',
        'average_speed', 'traffic_delay', 'weather_delay', 'boarding_delay',
        'total_delay', 'headway_minutes', 'historical_route_average',
        'historical_stop_average', 'historical_hour_average',
        'historical_peak_average', 'historical_weekend_average',
        'route_popularity_score', 'vehicle_capacity', 'passenger_count'
    }
    
    def __init__(self):
        """Initialize the preprocessor."""
        self.feature_names = None
        self.categorical_features = None
        self.target_column = config.get('target_column', 'passenger_count')
        
    def load_dataset(self, path: str = None) -> pd.DataFrame:
        """
        Load the synthetic passenger demand dataset.
        
        Args:
            path: Path to the dataset CSV file
            
        Returns:
            Loaded DataFrame
        """
        if path is None:
            path = config.get('dataset_path')
        
        logger.info(f"Loading dataset from {path}")
        
        try:
            df = pd.read_csv(path, encoding='utf-8')
            logger.info(f"Loaded {len(df)} records with {len(df.columns)} columns")
            return df
        except Exception as e:
            logger.error(f"Failed to load dataset: {e}")
            raise
    
    def validate_schema(self, df: pd.DataFrame) -> bool:
        """
        Validate that the DataFrame matches the expected schema.
        
        Args:
            df: DataFrame to validate
            
        Returns:
            True if validation passes, raises exception otherwise
        """
        logger.info("Validating dataset schema...")
        
        # Check for required columns
        missing_cols = set(self.EXPECTED_SCHEMA.keys()) - set(df.columns)
        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")
        
        # Check for extra columns
        extra_cols = set(df.columns) - set(self.EXPECTED_SCHEMA.keys())
        if extra_cols:
            logger.warning(f"Extra columns found (will be ignored): {extra_cols}")
        
        # Check data types
        type_mismatches = []
        for col, expected_type in self.EXPECTED_SCHEMA.items():
            if col in df.columns:
                actual_type = str(df[col].dtype)
                # Allow some flexibility in type matching
                if 'int' in expected_type and 'int' not in actual_type.lower():
                    if 'float' not in actual_type.lower():  # Allow float for int
                        type_mismatches.append((col, expected_type, actual_type))
                elif 'float' in expected_type and 'float' not in actual_type.lower():
                    if 'int' not in actual_type.lower():  # Allow int for float
                        type_mismatches.append((col, expected_type, actual_type))
                elif 'object' in expected_type and 'object' not in actual_type.lower():
                    type_mismatches.append((col, expected_type, actual_type))
        
        if type_mismatches:
            logger.warning(f"Type mismatches found (will attempt conversion): {type_mismatches}")
        
        logger.info("Schema validation passed")
        return True
    
    def convert_data_types(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Convert columns to appropriate data types.
        
        Args:
            df: DataFrame to convert
            
        Returns:
            DataFrame with converted types
        """
        logger.info("Converting data types...")
        
        df = df.copy()
        
        # Convert datetime
        if 'service_date' in df.columns:
            df['service_date'] = pd.to_datetime(df['service_date'])
        
        # Convert numeric columns
        # NOTE: Leakage features removed: boarding_count, alighting_count, onboard_passengers, occupancy_ratio, load_factor
        numeric_cols = [
            'route_type', 'direction_id', 'stop_sequence', 'stop_lat', 'stop_lon',
            'terminal_stop_flag', 'major_interchange_flag', 'cumulative_distance',
            'remaining_distance', 'number_of_stops', 'remaining_stops',
            'route_length_km', 'scheduled_trip_duration', 'trip_start_time',
            'trip_end_time', 'hour', 'minute', 'month', 'holiday_flag',
            'peak_hour_flag', 'temperature', 'rainfall_flag', 'congestion_index',
            'average_speed', 'traffic_delay', 'weather_delay', 'boarding_delay',
            'total_delay', 'headway_minutes', 'historical_route_average',
            'historical_stop_average', 'historical_hour_average',
            'historical_peak_average', 'historical_weekend_average',
            'route_popularity_score', 'vehicle_capacity', 'passenger_count'
        ]
        
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Convert categorical columns to string
        for col in self.CATEGORICAL_FEATURES:
            if col in df.columns:
                df[col] = df[col].astype(str)
        
        logger.info("Data type conversion completed")
        return df
    
    def identify_categorical_features(self, df: pd.DataFrame) -> List[str]:
        """
        Identify categorical features in the DataFrame.
        
        Args:
            df: DataFrame to analyze
            
        Returns:
            List of categorical feature names
        """
        logger.info("Identifying categorical features...")
        
        # Use predefined categorical features
        categorical_features = [col for col in self.CATEGORICAL_FEATURES if col in df.columns]
        
        # Also auto-detect categorical features based on cardinality
        # BUT exclude numeric columns that should never be categorical
        threshold = config.get('categorical_threshold', 10)
        for col in df.columns:
            if col not in categorical_features and col != self.target_column:
                # Skip if it's a known numeric column
                if col in self.NUMERIC_COLUMNS:
                    continue
                # Only auto-detect if it's object type or has very few unique values
                unique_count = df[col].nunique()
                if df[col].dtype == 'object' or (df[col].dtype in ['int64', 'float64'] and unique_count <= threshold):
                    categorical_features.append(col)
        
        logger.info(f"Identified {len(categorical_features)} categorical features")
        return categorical_features
    
    def prepare_features(
        self,
        df: pd.DataFrame,
        for_training: bool = True
    ) -> Tuple[pd.DataFrame, pd.Series, List[str]]:
        """
        Prepare features for CatBoost training or inference.
        
        Args:
            df: Input DataFrame
            for_training: Whether preparing for training (includes target)
            
        Returns:
            Tuple of (features DataFrame, target Series, categorical feature list)
        """
        logger.info("Preparing features for CatBoost...")
        
        # Validate schema
        self.validate_schema(df)
        
        # Convert data types
        df = self.convert_data_types(df)
        
        # Identify categorical features
        self.categorical_features = self.identify_categorical_features(df)
        
        # Get feature names (exclude target and excluded features)
        exclude_features = config.get('exclude_features', [])
        leakage_features = [
            'boarding_count', 'alighting_count', 'onboard_passengers', 
            'occupancy_ratio', 'load_factor', 'demand_class',
            'congestion_index', 'traffic_delay', 'total_delay'
        ]
        exclude_features = exclude_features + [self.target_column] + leakage_features
        
        self.feature_names = [col for col in df.columns if col not in exclude_features]
        
        # Ensure categorical features are in feature names
        self.categorical_features = [col for col in self.categorical_features if col in self.feature_names]
        
        # Prepare features and target
        X = df[self.feature_names].copy()
        
        if for_training:
            y = df[self.target_column].copy()
            # Handle missing values in target
            y = y.fillna(0)
        else:
            y = None
        
        logger.info(f"Prepared {len(X)} samples with {len(self.feature_names)} features")
        logger.info(f"Categorical features: {len(self.categorical_features)}")
        
        return X, y, self.categorical_features
    
    def split_chronologically(
        self,
        df: pd.DataFrame,
        date_column: str = 'service_date'
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        Split data chronologically by service_date.
        
        Args:
            df: DataFrame to split
            date_column: Name of the date column to split on
            
        Returns:
            Tuple of (train_df, val_df, test_df)
        """
        logger.info("Splitting data chronologically...")
        
        # Sort by date
        df = df.sort_values(date_column).reset_index(drop=True)
        
        # Calculate split indices
        n = len(df)
        train_end = int(n * config.get('train_split', 0.70))
        val_end = train_end + int(n * config.get('val_split', 0.15))
        
        train_df = df.iloc[:train_end].copy()
        val_df = df.iloc[train_end:val_end].copy()
        test_df = df.iloc[val_end:].copy()
        
        logger.info(f"Train: {len(train_df)} ({len(train_df)/n*100:.1f}%)")
        logger.info(f"Validation: {len(val_df)} ({len(val_df)/n*100:.1f}%)")
        logger.info(f"Test: {len(test_df)} ({len(test_df)/n*100:.1f}%)")
        
        # Log date ranges
        if date_column in df.columns:
            logger.info(f"Train date range: {train_df[date_column].min()} to {train_df[date_column].max()}")
            logger.info(f"Validation date range: {val_df[date_column].min()} to {val_df[date_column].max()}")
            logger.info(f"Test date range: {test_df[date_column].min()} to {test_df[date_column].max()}")
        
        return train_df, val_df, test_df
    
    def get_feature_names(self) -> List[str]:
        """Get the feature names used during preprocessing."""
        return self.feature_names if self.feature_names else []
    
    def get_categorical_features(self) -> List[str]:
        """Get the categorical feature names."""
        return self.categorical_features if self.categorical_features else []


def load_and_preprocess_data(
    dataset_path: str = None,
    for_training: bool = True
) -> Tuple[pd.DataFrame, pd.Series, List[str]]:
    """
    Convenience function to load and preprocess data.
    
    Args:
        dataset_path: Path to dataset
        for_training: Whether for training (includes target)
        
    Returns:
        Tuple of (features, target, categorical_features)
    """
    preprocessor = DataPreprocessor()
    df = preprocessor.load_dataset(dataset_path)
    X, y, cat_features = preprocessor.prepare_features(df, for_training=for_training)
    return X, y, cat_features
