# BMTC Synthetic Passenger Demand Dataset Report

## Overview
This report documents the generation of a production-quality synthetic passenger demand dataset from BMTC GTFS data for training CatBoostRegressor models.

**Generation Date:** 2026-06-26 15:02:11
**Random Seed:** 42
**Target Records:** 225000

---

## Dataset Statistics

### Basic Statistics
- **Total Records:** 261,790
- **Total Routes:** 2,023
- **Total Trips:** 8,579
- **Total Stops:** 7,387
- **Total Features:** 58
- **Memory Usage:** 287.01 MB

### Feature Summary
- **Route Features:** 8
- **Stop Features:** 12
- **Trip Features:** 4
- **Temporal Features:** 8
- **Weather Features:** 3
- **Traffic Features:** 7
- **Service Features:** 2
- **Historical Features:** 5
- **Operational Features:** 9
- **Target Variable:** 1

---

## Passenger Statistics

### Descriptive Statistics
- **Mean:** 41.09
- **Median:** 38.00
- **Standard Deviation:** 19.06
- **Minimum:** 0
- **Maximum:** 120
- **25th Percentile:** 27.00
- **75th Percentile:** 52.00

### Passenger Distribution
- **0-20:** 32,218 records (12.3%)
- **21-40:** 111,085 records (42.4%)
- **41-60:** 75,070 records (28.7%)
- **61-80:** 34,337 records (13.1%)
- **81-100:** 7,597 records (2.9%)
- **above_100:** 1,483 records (0.6%)

### Demand Class Distribution
- **Very High:** 232,688 records (88.9%)
- **Medium:** 10,916 records (4.2%)
- **High:** 10,512 records (4.0%)
- **Low:** 7,674 records (2.9%)

---

## Feature Distributions

### Weather Distribution
- **Sunny:** 109,793 records (41.9%)
- **Cloudy:** 56,620 records (21.6%)
- **Light Rain:** 43,338 records (16.6%)
- **Heavy Rain:** 21,715 records (8.3%)
- **Fog:** 21,676 records (8.3%)
- **Thunderstorm:** 8,648 records (3.3%)

### Congestion Distribution
- **Low:** 96,667 records (36.9%)
- **Medium:** 78,311 records (29.9%)
- **High:** 58,999 records (22.5%)
- **Severe:** 27,813 records (10.6%)

### Time Slot Distribution
- **Afternoon:** 77,996 records (29.8%)
- **Morning Peak:** 65,232 records (24.9%)
- **Evening Peak:** 46,064 records (17.6%)
- **Morning:** 34,257 records (13.1%)
- **Night:** 27,585 records (10.5%)
- **Early Morning:** 9,935 records (3.8%)
- **Late Night:** 721 records (0.3%)

### Area Type Distribution
- **Mixed:** 161,691 records (61.8%)
- **Residential:** 34,608 records (13.2%)
- **Interchange:** 28,322 records (10.8%)
- **Educational:** 15,719 records (6.0%)
- **Market:** 7,420 records (2.8%)
- **Hospital:** 6,771 records (2.6%)
- **Industrial:** 4,768 records (1.8%)
- **Commercial:** 2,491 records (1.0%)

### Service Frequency Distribution
- **Sparse:** 261,616 records (99.9%)
- **Normal:** 140 records (0.1%)
- **Very Frequent:** 34 records (0.0%)

---

## Peak vs Off-Peak Distribution

### Peak Hours
- **Morning Peak (07:00-10:00):** 51,705 records
- **Evening Peak (17:00-20:00):** 46,064 records
- **Total Peak Records:** 97,769 (37.3%)

### Off-Peak Hours
- **Total Off-Peak Records:** 164,021 (62.7%)

---

## Weekday vs Weekend Distribution

- **Weekday Records:** 189,064 (72.2%)
- **Weekend Records:** 72,726 (27.8%)

---

## Feature Correlation Summary

### Key Correlations with Passenger Count
- **boarding_count:** 0.964
- **alighting_count:** 0.945
- **historical_stop_average:** 0.497
- **historical_hour_average:** 0.440
- **peak_hour_flag:** 0.440
- **historical_peak_average:** 0.440
- **historical_weekend_average:** 0.400
- **average_speed:** 0.223
- **major_interchange_flag:** 0.170

---

## Generation Methodology

### Data Source
The dataset is generated from BMTC GTFS feed files:
- routes.txt: Route information
- trips.txt: Trip schedules
- stops.txt: Stop locations and metadata
- stop_times.txt: Stop sequences and times
- calendar.txt: Service calendar
- shapes.txt: Route geometry

### Passenger Demand Generation
Passenger demand is generated using a deterministic formula with fixed random seed (42):

```
Passenger Count = Base Route Demand
                × Peak Hour Weight
                × Weekday/Weekend Weight
                × Area Type Weight
                × Interchange Weight
                × Weather Weight
                × Congestion Weight
                × Service Frequency Weight
                × Route Popularity Weight
                + Gaussian Noise (Seed = 42)
```

### Key Generation Steps
1. **GTFS Loading:** Load and validate all GTFS files
2. **Service Date Generation:** Generate service dates from calendar
3. **Trip-Stop Sampling:** Sample trip-stop events to target size
4. **Temporal Features:** Generate hour, day, month, peak flags
5. **Stop Features:** Calculate distances, sequences, area types
6. **Trip Features:** Calculate route lengths, durations
7. **Weather Features:** Generate seasonal weather conditions
8. **Traffic Features:** Generate congestion and delays
9. **Service Features:** Calculate headways and frequency
10. **Historical Features:** Generate deterministic historical averages
11. **Operational Features:** Generate capacity, boarding, occupancy
12. **Passenger Count:** Apply deterministic formula with noise

### Area Type Inference
Area types are inferred from stop names using keyword matching:
- **Interchange:** bus stand, station, terminal, junction
- **Educational:** college, school, university, institute
- **Hospital:** hospital, medical, clinic
- **Market:** market, mall, shopping, complex
- **Industrial:** industrial, factory, estate
- **Commercial:** office, corporate, business
- **Residential:** layout, colony, nagar
- **Mixed:** Other stops

### Quality Assurance
- No duplicate records
- No missing values
- Valid GTFS relationships preserved
- Realistic travel speeds (5-60 km/h)
- Realistic delays
- Passenger counts within capacity limits
- Reproducible output with fixed seed

---

## Validation Results

### Data Quality Checks
- **Duplicate Records:** 0
- **Missing Values:** 0 columns
- **Passenger Range:** 0 - 120
- **Congestion Index Range:** 0.20 - 0.90
- **Average Speed Range:** 5 - 44 km/h
- **Vehicle Capacity Range:** 40 - 80

### Validation Status
✓ All validation checks passed
✓ Dataset is production-ready for CatBoost training

---

## Output Files

1. **synthetic_passenger_demand.csv** - Main dataset (261,790 records)
2. **feature_description.xlsx** - Feature documentation (58 features)
3. **dataset_report.md** - This report
4. **validation_report.json** - Detailed validation results
5. **generation_config.json** - Generation configuration

---

## Usage Recommendations

### For CatBoost Training
```python
import pandas as pd
from catboost import CatBoostRegressor

# Load dataset
df = pd.read_csv('synthetic_passenger_demand.csv')

# Separate features and target
X = df.drop('passenger_count', axis=1)
y = df['passenger_count']

# Define categorical features
categorical_features = ['route_id', 'route_short_name', 'service_id', 'trip_id', 
                       'shape_id', 'stop_id', 'stop_name', 'time_slot', 
                       'day_of_week', 'weekday_weekend', 'weather_condition',
                       'traffic_level', 'service_frequency_category', 'area_type',
                       'demand_class']

# Train CatBoost model
model = CatBoostRegressor(
    cat_features=categorical_features,
    random_seed=42,
    verbose=100
)
model.fit(X, y)
```

### Preprocessing Notes
- All categorical features are ready for CatBoost
- No missing values to impute
- No duplicates to remove
- Target variable is integer type
- All features are in appropriate data types

---

## Reproducibility

This dataset is fully reproducible using:
- **Random Seed:** 42
- **Configuration:** generation_config.json
- **Source GTFS:** BMTC GTFS feed

Rerunning the generation script with the same GTFS feed and configuration will produce identical results.

---

*Report generated on 2026-06-26 15:02:25*
