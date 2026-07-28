"""
Clean dataset by removing leakage features.
Removes: boarding_count, alighting_count, onboard_passengers, occupancy_ratio, load_factor, demand_class
"""

import pandas as pd
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def clean_dataset(input_path: str, output_path: str) -> None:
    """
    Remove leakage features from dataset.
    
    Args:
        input_path: Path to input CSV
        output_path: Path to output CSV
    """
    logger.info(f"Loading dataset from {input_path}")
    df = pd.read_csv(input_path)
    
    logger.info(f"Original shape: {df.shape}")
    logger.info(f"Original columns: {len(df.columns)}")
    
    # Leakage features to remove
    leakage_features = [
        'boarding_count',
        'alighting_count',
        'onboard_passengers',
        'occupancy_ratio',
        'load_factor',
        'demand_class'
    ]
    
    # Check which features exist
    features_to_drop = [f for f in leakage_features if f in df.columns]
    logger.info(f"Leakage features to remove: {features_to_drop}")
    
    # Drop leakage features
    df_clean = df.drop(columns=features_to_drop)
    
    logger.info(f"Cleaned shape: {df_clean.shape}")
    logger.info(f"Cleaned columns: {len(df_clean.columns)}")
    logger.info(f"Removed {len(features_to_drop)} leakage features")
    
    # Save cleaned dataset
    df_clean.to_csv(output_path, index=False)
    logger.info(f"Cleaned dataset saved to {output_path}")
    
    return df_clean

if __name__ == "__main__":
    base_dir = Path(__file__).parent.parent
    input_path = base_dir / "DataSet" / "syn_data" / "synthetic_passenger_demand.csv"
    output_path = base_dir / "DataSet" / "syn_data" / "synthetic_passenger_demand_clean.csv"
    
    clean_dataset(str(input_path), str(output_path))
