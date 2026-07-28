"""
Extract real route metadata from GTFS files to select diverse routes for audit.
"""
import pandas as pd
import numpy as np

# Load GTFS data
routes = pd.read_csv('DataSet/real_data/routes.txt')
trips = pd.read_csv('DataSet/real_data/trips.txt')
stop_times = pd.read_csv('DataSet/real_data/stop_times.txt')
stops = pd.read_csv('DataSet/real_data/stops.txt')

print("Routes columns:", list(routes.columns))
print("Trips columns:", list(trips.columns))
print("Stop times columns:", list(stop_times.columns))
print(f"Routes: {len(routes)}, Trips: {len(trips)}")

# Get number of stops per trip, then average per route
print("\nSample routes:")
print(routes.head(10))
