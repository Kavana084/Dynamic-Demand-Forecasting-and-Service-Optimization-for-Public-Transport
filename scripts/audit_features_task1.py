import json
import pandas as pd
import os

def audit_features():
    # 3. Features present in processed_dataset.csv
    try:
        df = pd.read_csv('outputs/processed_dataset.csv', nrows=5)
        processed_features = list(df.columns)
    except Exception as e:
        processed_features = []
        print(f"Error reading processed_dataset: {e}")

    if processed_features:
        actual_training_features = [c for c in processed_features if c != 'passenger_count' and c != 'service_date']
    else:
        actual_training_features = []

    inference_features = [
        'route_id', 'route_short_name', 'route_type', 'service_id', 'trip_id', 'shape_id', 'direction_id',
        'stop_id', 'stop_name', 'stop_sequence', 'stop_lat', 'stop_lon', 'terminal_stop_flag', 'major_interchange_flag', 'area_type',
        'cumulative_distance', 'remaining_distance', 'number_of_stops', 'remaining_stops',
        'route_length_km', 'scheduled_trip_duration', 'trip_start_time', 'trip_end_time',
        'hour', 'minute', 'time_slot', 'day_of_week', 'weekday_weekend', 'month', 'holiday_flag', 'peak_hour_flag',
        'weather_condition', 'temperature', 'rainfall_flag',
        'congestion_index', 'traffic_level', 'average_speed', 'traffic_delay', 'weather_delay', 'boarding_delay', 'total_delay',
        'headway_minutes', 'service_frequency_category',
        'historical_route_average', 'historical_stop_average', 'historical_hour_average', 'historical_peak_average', 'historical_weekend_average',
        'route_popularity_score', 'vehicle_capacity',
        'boarding_count', 'alighting_count', 'onboard_passengers', 'occupancy_ratio', 'load_factor', 'demand_class'
    ]

    leakage_features = ['boarding_count', 'alighting_count', 'onboard_passengers', 'occupancy_ratio', 'load_factor', 'demand_class']
    
    synthetic_only_features = ['boarding_delay', 'total_delay', 'route_popularity_score', 'boarding_count', 'alighting_count', 'onboard_passengers', 'occupancy_ratio', 'load_factor', 'demand_class']

    unused_features = [f for f in processed_features if f not in actual_training_features and f != 'passenger_count']

    report = {
        "training_features": actual_training_features,
        "inference_features": inference_features,
        "processed_dataset_features": processed_features,
        "synthetic_only_features": synthetic_only_features,
        "leakage_features": leakage_features,
        "unused_features": unused_features
    }

    with open('outputs/feature_audit_report.json', 'w') as f:
        json.dump(report, f, indent=4)
        
if __name__ == "__main__":
    audit_features()
