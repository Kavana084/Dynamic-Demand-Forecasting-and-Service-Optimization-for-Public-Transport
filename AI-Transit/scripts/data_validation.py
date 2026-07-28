import pandas as pd
import numpy as np
import json
from collections import Counter

class DatasetValidator:
    def __init__(self, dataset_path: str):
        self.dataset_path = dataset_path
        self.issues = []
        try:
            self.df = pd.read_json(dataset_path)
            self.data_dict = self._load_json(dataset_path)
        except Exception as e:
            self.df = pd.DataFrame()
            self.data_dict = []
            self.issues.append(f"Failed to load dataset: {str(e)}")

    def _load_json(self, file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    # ----------------------------
    # 1. EDA SUMMARY
    # ----------------------------
    def eda_summary(self):
        print("\n========== EDA SUMMARY ==========")
        print("Total Records:", len(self.data_dict))
        
        if not self.data_dict:
            return

        missing = sum(1 for record in self.data_dict for v in record.values() if v is None)
        print("Missing Values (dict check):", missing)

        routes = set(record.get("route_id") for record in self.data_dict if "route_id" in record)
        print("Unique Routes:", len(routes))

        stops = set(record.get("stop_id") for record in self.data_dict if "stop_id" in record)
        print("Unique Stops:", len(stops))

        if "passenger_count" in self.df.columns:
            print("Min Passenger Count:", self.df["passenger_count"].min())
            print("Max Passenger Count:", self.df["passenger_count"].max())
            print("Average Passenger Count:", round(self.df["passenger_count"].mean(), 2))

        if "weather" in self.df.columns:
            weather_counts = Counter(record.get("weather") for record in self.data_dict if "weather" in record)
            print("\nWeather Distribution:")
            for weather, count in weather_counts.items():
                print(f"  {weather}: {count}")

        if "traffic_level" in self.df.columns:
            traffic_counts = Counter(record.get("traffic_level") for record in self.data_dict if "traffic_level" in record)
            print("\nTraffic Distribution:")
            for traffic, count in traffic_counts.items():
                print(f"  {traffic}: {count}")

        if "peak_hour" in self.df.columns:
            peak_count = self.df["peak_hour"].sum()
            print("\nPeak Hour Records:", peak_count)

        if "holiday" in self.df.columns:
            holiday_count = self.df["holiday"].sum()
            print("Holiday Records:", holiday_count)
            
        print("=================================\n")

    # ----------------------------
    # 2. COLUMN VALIDATION
    # ----------------------------
    def check_columns(self, required_columns):
        if self.df.empty: return
        missing = [col for col in required_columns if col not in self.df.columns]
        if missing:
            self.issues.append(f"Missing columns: {missing}")
        else:
            print("✔ Column check passed")

    # ----------------------------
    # 3. DATA TYPES + NULL CHECK
    # ----------------------------
    def check_nulls(self, threshold=0.3):
        if self.df.empty: return
        null_ratios = self.df.isnull().mean()
        high_nulls = null_ratios[null_ratios > threshold].to_dict()
        if high_nulls:
            self.issues.append(f"High null columns (> {threshold*100}%): {high_nulls}")
        else:
            print("✔ Null check passed")

    # ----------------------------
    # 4. DATE/TIME VALIDATION
    # ----------------------------
    def check_dates(self, date_column="timestamp"):
        if self.df.empty: return
        if date_column not in self.df.columns:
            self.issues.append(f"Missing date column: {date_column}")
            return
        try:
            temp_dates = pd.to_datetime(self.df[date_column], errors="coerce")
            invalid_dates = temp_dates[temp_dates.isnull()]
            if len(invalid_dates) > 0:
                self.issues.append(f"Invalid timestamps found: {len(invalid_dates)} rows")
            else:
                print("✔ Date validation passed")
        except Exception as e:
            self.issues.append(f"Date parsing error: {str(e)}")

    # ----------------------------
    # 5. PASSENGER VARIATION CHECK
    # ----------------------------
    def check_passenger_variation(self, col="passenger_count"):
        if self.df.empty: return
        if col not in self.df.columns:
            self.issues.append(f"Missing passenger column: {col}")
            return
        mean = self.df[col].mean()
        std = self.df[col].std()
        if std == 0 or np.isnan(std):
            self.issues.append(f"Passenger count has no variation (std=0) in column {col}")
        else:
            print(f"✔ Passenger variation OK | mean={mean:.2f}, std={std:.2f}")

    # ----------------------------
    # 6. DELAY STATISTICS CHECK
    # ----------------------------
    def check_delay_stats(self, col="delay_minutes"):
        if self.df.empty: return
        if col not in self.df.columns:
            self.issues.append(f"Missing delay column: {col}")
            return
        negative_delays = self.df[self.df[col] < -5]
        extreme_delays = self.df[self.df[col] > 180]
        if len(negative_delays) > 0:
            self.issues.append(f"Unrealistic negative delays: {len(negative_delays)}")
        if len(extreme_delays) > 0:
            self.issues.append(f"Extreme delays (>180 min): {len(extreme_delays)}")
        print("✔ Delay stats checked")

    # ----------------------------
    # 7. ROUTE / STOP VALIDATION
    # ----------------------------
    def check_ids(self):
        if self.df.empty: return
        for col in ["route_id", "stop_id", "trip_id"]:
            if col in self.df.columns:
                nulls = self.df[col].isnull().sum()
                if nulls > 0:
                    self.issues.append(f"{col} has {nulls} missing values")
        print("✔ ID validation done")

    # ----------------------------
    # 8. DUPLICATE CHECK
    # ----------------------------
    def check_duplicates(self):
        if self.df.empty: return
        dup_count = self.df.duplicated().sum()
        if dup_count > 0:
            self.issues.append(f"Duplicate rows found: {dup_count}")
        else:
            print("✔ No duplicates found")

    # ----------------------------
    # FINAL REPORT
    # ----------------------------
    def report(self):
        print("\n========== DATASET VALIDATION REPORT ==========")
        if not self.issues:
            print("✔ Dataset is CLEAN and READY for ML training")
        else:
            print("⚠ Issues found:")
            for i, issue in enumerate(self.issues, 1):
                print(f"{i}. {issue}")
        print("===============================================")


if __name__ == "__main__":
    file_path = r"F:\transit-ai-system\DataSet\dataset\historical_dataset_v3.json"
    
    validator = DatasetValidator(file_path)
    validator.eda_summary()
    
    required_columns = [
        "route_id",
        "stop_id",
        "trip_id",
        "passenger_count",
        "delay_minutes",
        "traffic_level",
        "weather"
    ]

    validator.check_columns(required_columns)
    validator.check_nulls()
    # validator.check_dates("timestamp")
    validator.check_passenger_variation()
    validator.check_delay_stats()
    validator.check_ids()
    validator.check_duplicates()

    validator.report()
