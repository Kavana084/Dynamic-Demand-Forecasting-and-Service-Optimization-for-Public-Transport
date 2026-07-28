import sqlite3
import pandas as pd
import numpy as np
import joblib
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

DB_PATH = "transit_data.db"
MODEL_PATH = "catboost_model.pkl"


# -------------------------
# LOAD DATA
# -------------------------
def load_data():
    conn = sqlite3.connect(DB_PATH)

    df = pd.read_sql("""
        SELECT
            route_id,
            stop_id,
            hour,
            weekday,
            weather,
            temperature,
            rainfall,
            delay_minutes,
            congestion_score,
            passenger_count,
            timestamp
        FROM transit_observations
    """, conn)

    conn.close()

    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp")

    return df


# -------------------------
# LOAD MODEL
# -------------------------
def load_model():
    return joblib.load(MODEL_PATH)


# -------------------------
# PREPARE FEATURES
# -------------------------
def prepare_features(df):
    X = df.drop(columns=["passenger_count", "timestamp"])
    y = df["passenger_count"]
    return X, y


# -------------------------
# GLOBAL METRICS
# -------------------------
def global_metrics(y_true, y_pred):
    print("\n OVERALL PERFORMANCE")
    print("-" * 40)
    print("MAE :", mean_absolute_error(y_true, y_pred))
    print("RMSE:", np.sqrt(mean_squared_error(y_true, y_pred)))
    print("R2  :", r2_score(y_true, y_pred))


# -------------------------
# ROUTE-WISE ANALYSIS
# -------------------------
def route_wise_analysis(df, y_true, y_pred):
    df = df.copy()
    df["y_true"] = y_true
    df["y_pred"] = y_pred
    df["error"] = abs(df["y_true"] - df["y_pred"])

    print("\n🛣 ROUTE-WISE ERROR ANALYSIS")
    print("-" * 40)

    route_stats = df.groupby("route_id")["error"].mean().sort_values(ascending=False)

    print(route_stats.head(10))


# -------------------------
# TIME-WISE ANALYSIS
# -------------------------
def time_wise_analysis(df, y_true, y_pred):
    df = df.copy()
    df["y_true"] = y_true
    df["y_pred"] = y_pred
    df["error"] = abs(df["y_true"] - df["y_pred"])

    print("\n TIME-WISE ERROR ANALYSIS")
    print("-" * 40)

    hour_stats = df.groupby("hour")["error"].mean()

    for hour, err in hour_stats.items():
        print(f"Hour {hour}: MAE = {err:.3f}")


# -------------------------
# BIAS CHECK
# -------------------------
def bias_analysis(y_true, y_pred):
    error = np.array(y_pred) - np.array(y_true)

    print("\n⚖ BIAS ANALYSIS")
    print("-" * 40)
    print("Mean Error (Bias):", np.mean(error))

    if np.mean(error) > 0:
        print("Model is OVER-predicting demand")
    else:
        print("Model is UNDER-predicting demand")


# -------------------------
# MAIN
# -------------------------
def main():
    print(" Loading data...")
    df = load_data()

    print(" Loading model...")
    model = load_model()

    X, y = prepare_features(df)

    print(" Running predictions...")
    y_pred = model.predict(X)

    global_metrics(y, y_pred)
    route_wise_analysis(df, y, y_pred)
    time_wise_analysis(df, y, y_pred)
    bias_analysis(y, y_pred)


if __name__ == "__main__":
    main()