"""
=============================================================================
POST-RETRAIN VALIDATION AUDIT
CatBoost Passenger Demand Model — Physical Realism and Variance Check
=============================================================================

Objective:
  Verify that the retrained CatBoost model produces physically realistic,
  non-constant demand predictions across diverse routes and scenarios.

Outputs:
  outputs/post_retrain_validation_report.json
  outputs/model_readiness_report.json

Verdict Scale:
  A = Production Ready
  B = Acceptable for Pilot
  C = Requires Dataset Rebuild

Fix notes:
  - service_date is numeric feature_idx=0; pass as ordinal integer (days since
    proleptic Gregorian epoch) so CatBoost can parse it as float.
  - Guard added for empty prediction array before numpy reductions.
============================================================================="""

import os
import sys
import json
import logging
import warnings
import math
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple
from itertools import product as iproduct

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
os.environ["PYTHONIOENCODING"] = "utf-8"

# Path setup
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("validate_retrained_model")

# CatBoost
try:
    from catboost import CatBoostRegressor, Pool
    log.info("CatBoost imported successfully.")
except ImportError as exc:
    log.critical("CatBoost not installed: %s", exc)
    sys.exit(1)


# =============================================================================
# CONSTANTS AND PATHS
# =============================================================================

MODEL_PATH      = ROOT / "outputs" / "models" / "catboost_demand_model.cbm"
CONFIG_PATH     = ROOT / "outputs" / "model_config.json"
METRICS_PATH    = ROOT / "outputs" / "training_metrics.json"
GTFS_ROUTES     = ROOT / "DataSet" / "real_data" / "routes.txt"
GTFS_TRIPS      = ROOT / "DataSet" / "real_data" / "trips.txt"
GTFS_STOP_TIMES = ROOT / "DataSet" / "real_data" / "stop_times.txt"
OUTPUT_DIR      = ROOT / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

VALIDATION_REPORT = OUTPUT_DIR / "post_retrain_validation_report.json"
READINESS_REPORT  = OUTPUT_DIR / "model_readiness_report.json"

# Time scenarios
TIME_SCENARIOS: Dict[str, Dict] = {
    "Morning Peak": {
        "hour": 8, "minute": 0, "peak_hour_flag": 1,
        "time_slot": "Morning Peak", "is_peak": True,
    },
    "Afternoon Off-Peak": {
        "hour": 14, "minute": 0, "peak_hour_flag": 0,
        "time_slot": "Afternoon", "is_peak": False,
    },
    "Evening Peak": {
        "hour": 18, "minute": 0, "peak_hour_flag": 1,
        "time_slot": "Evening Peak", "is_peak": True,
    },
    "Night": {
        "hour": 22, "minute": 0, "peak_hour_flag": 0,
        "time_slot": "Night", "is_peak": False,
    },
}

# Weather scenarios
WEATHER_SCENARIOS: Dict[str, Dict] = {
    "Clear": {
        "weather_condition": "Clear",
        "rainfall_flag": 0,
        "temperature": 28,
        "weather_delay": 0,
    },
    "Rainy": {
        "weather_condition": "Rainy",
        "rainfall_flag": 1,
        "temperature": 22,
        "weather_delay": 5,
    },
}

# Traffic scenarios
TRAFFIC_SCENARIOS: Dict[str, Dict] = {
    "Low": {
        "traffic_level": "Low",
        "congestion_index": 0.2,
        "average_speed": 45,
        "traffic_delay": 0,
    },
    "Medium": {
        "traffic_level": "Medium",
        "congestion_index": 0.5,
        "average_speed": 30,
        "traffic_delay": 5,
    },
    "Heavy": {
        "traffic_level": "Heavy",
        "congestion_index": 0.85,
        "average_speed": 15,
        "traffic_delay": 15,
    },
}

# Historical calibration per category
CATEGORY_HIST: Dict[str, Dict] = {
    "short":        {"hist_route": 18.0,  "hist_stop": 12.0, "hist_peak": 28.0,  "hist_wknd": 10.0, "pop": 0.35},
    "medium":       {"hist_route": 35.0,  "hist_stop": 22.0, "hist_peak": 52.0,  "hist_wknd": 24.0, "pop": 0.55},
    "long":         {"hist_route": 55.0,  "hist_stop": 35.0, "hist_peak": 80.0,  "hist_wknd": 40.0, "pop": 0.70},
    "hub":          {"hist_route": 72.0,  "hist_stop": 48.0, "hist_peak": 105.0, "hist_wknd": 55.0, "pop": 0.90},
    "feeder":       {"hist_route": 14.0,  "hist_stop": 9.0,  "hist_peak": 20.0,  "hist_wknd": 7.0,  "pop": 0.25},
    "supplemental": {"hist_route": 30.0,  "hist_stop": 18.0, "hist_peak": 45.0,  "hist_wknd": 20.0, "pop": 0.45},
}

HOUR_AVG: Dict[int, float]    = {8: 45.0, 14: 28.0, 18: 50.0, 22: 15.0}
HEADWAY_CAT: Dict[str, int]   = {"short": 20, "medium": 15, "long": 30, "hub": 8, "feeder": 25, "supplemental": 18}
SVC_FREQ: Dict[int, str]      = {8: "High", 15: "High", 18: "Medium", 20: "Medium", 25: "Low", 30: "Low"}
MIN_PER_CAT = 4


# =============================================================================
# MODEL LOADING
# =============================================================================

def load_model_artifacts() -> Tuple[CatBoostRegressor, Dict, Dict]:
    log.info("=" * 60)
    log.info("LOADING MODEL ARTIFACTS")
    log.info("=" * 60)

    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Model not found: {MODEL_PATH}")

    model = CatBoostRegressor()
    model.load_model(str(MODEL_PATH))
    log.info("Model loaded | trees=%d | native-features=%d", model.tree_count_, len(model.feature_names_))

    cfg: Dict = {}
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
            cfg = json.load(fh)
        log.info("Config loaded | features=%d | categoricals=%d",
                 len(cfg.get("feature_names", [])), len(cfg.get("categorical_features", [])))
    else:
        log.warning("model_config.json missing — using introspection.")
        cfg["feature_names"] = list(model.feature_names_)
        cfg["categorical_features"] = []

    metrics: Dict = {}
    if METRICS_PATH.exists():
        with open(METRICS_PATH, "r", encoding="utf-8") as fh:
            metrics = json.load(fh)
        log.info("Metrics | RMSE=%.4f | MAE=%.4f | R2=%.4f",
                 metrics.get("RMSE", float("nan")),
                 metrics.get("MAE",  float("nan")),
                 metrics.get("R2",   float("nan")))

    return model, cfg, metrics


# =============================================================================
# GTFS ROUTE SELECTION
# =============================================================================

def compute_route_lengths_from_gtfs() -> pd.DataFrame:
    log.info("Loading GTFS files for route characterisation...")
    routes_df = pd.read_csv(GTFS_ROUTES, encoding="utf-8-sig")
    trips_df  = pd.read_csv(GTFS_TRIPS,  encoding="utf-8-sig")

    log.info("Streaming stop_times to count stops per trip...")
    chunks = pd.read_csv(
        GTFS_STOP_TIMES,
        encoding="utf-8-sig",
        usecols=["trip_id", "stop_sequence"],
        chunksize=500_000,
    )
    agg_list = []
    for chunk in chunks:
        agg_list.append(chunk.groupby("trip_id")["stop_sequence"].max().reset_index())
    stops_per_trip = (
        pd.concat(agg_list, ignore_index=True)
        .groupby("trip_id")["stop_sequence"].max()
        .reset_index()
    )
    stops_per_trip.columns = ["trip_id", "stop_count"]

    merged = trips_df.merge(stops_per_trip, on="trip_id", how="left")
    route_agg = (
        merged.groupby("route_id")["stop_count"]
        .agg(["mean", "count"])
        .reset_index()
    )
    route_agg.columns = ["route_id", "avg_stops", "trip_count"]

    result = routes_df.merge(route_agg, on="route_id", how="inner")
    result["avg_stops"] = result["avg_stops"].fillna(10).round(0).astype(int)
    # ~0.4 km between consecutive stops on average
    result["estimated_length_km"] = (result["avg_stops"] * 0.4).round(2)
    result["area_type"] = result["avg_stops"].apply(
        lambda s: "CBD" if s >= 25 else ("Suburban" if s >= 15 else "Rural")
    )
    tc75 = result["trip_count"].quantile(0.75)
    sc75 = result["avg_stops"].quantile(0.75)
    result["is_hub"] = (result["trip_count"] >= tc75) & (result["avg_stops"] >= sc75)

    log.info("GTFS analysis done | routes=%d", len(result))
    return result


def select_routes(route_df: pd.DataFrame) -> List[Dict]:
    log.info("Selecting representative routes...")
    df = route_df.dropna(subset=["avg_stops"]).copy()
    selected: List[Dict] = []
    seen: set = set()

    def pick(mask: "pd.Series[bool]", category: str, n: int = MIN_PER_CAT) -> None:
        cands = df[mask & ~df["route_id"].isin(seen)].sample(frac=1, random_state=42)
        for _, row in cands.head(n).iterrows():
            seen.add(row["route_id"])
            selected.append({
                "route_id":            str(row["route_id"]),
                "route_short_name":    str(row.get("route_short_name", row["route_id"])),
                "route_long_name":     str(row.get("route_long_name", ""))[:80],
                "route_type":          int(row.get("route_type", 3)),
                "avg_stops":           int(row["avg_stops"]),
                "estimated_length_km": float(row["estimated_length_km"]),
                "area_type":           str(row["area_type"]),
                "is_hub":              bool(row["is_hub"]),
                "category":            category,
            })

    pick(df["estimated_length_km"] < 5, "short")
    pick((df["estimated_length_km"] >= 5) & (df["estimated_length_km"] < 15), "medium")
    pick(df["estimated_length_km"] >= 15, "long")
    pick(df["is_hub"], "hub")
    pick(
        (~df["is_hub"]) & (df["avg_stops"] <= 12) & (df["estimated_length_km"] < 8),
        "feeder",
    )

    # Pad to 20 if needed
    if len(selected) < 20:
        remaining = df[~df["route_id"].isin(seen)]
        to_add = min(20 - len(selected), len(remaining))
        for _, row in remaining.sample(to_add, random_state=1).iterrows():
            selected.append({
                "route_id":            str(row["route_id"]),
                "route_short_name":    str(row.get("route_short_name", row["route_id"])),
                "route_long_name":     str(row.get("route_long_name", ""))[:80],
                "route_type":          int(row.get("route_type", 3)),
                "avg_stops":           int(row["avg_stops"]),
                "estimated_length_km": float(row["estimated_length_km"]),
                "area_type":           str(row["area_type"]),
                "is_hub":              bool(row["is_hub"]),
                "category":            "supplemental",
            })

    cats = sorted(set(r["category"] for r in selected))
    log.info("Selected %d routes | categories: %s", len(selected), cats)
    for r in selected:
        log.info("  [%-12s] %-8s  %.1f km  %2d stops  hub=%s",
                 r["category"], r["route_id"],
                 r["estimated_length_km"], r["avg_stops"],
                 "Y" if r["is_hub"] else "N")
    return selected


# =============================================================================
# FEATURE CONSTRUCTION
# =============================================================================

def build_feature_row(
    route: Dict,
    time_name: str,
    weather_name: str,
    traffic_name: str,
    feature_names: List[str],
    cat_features: List[str],
) -> pd.DataFrame:
    cat   = route["category"]
    tsz   = TIME_SCENARIOS[time_name]
    wsz   = WEATHER_SCENARIOS[weather_name]
    trsz  = TRAFFIC_SCENARIOS[traffic_name]
    hist  = CATEGORY_HIST.get(cat, CATEGORY_HIST["supplemental"])

    hour      = tsz["hour"]
    length_km = route["estimated_length_km"]
    n_stops   = route["avg_stops"]
    headway   = HEADWAY_CAT.get(cat, 18)
    svc_freq  = SVC_FREQ.get(headway, "Medium")
    speed     = trsz["average_speed"]

    trip_dur  = max(5, int((length_km / speed) * 60)) if speed > 0 else 45
    t_start   = hour * 60
    t_end     = t_start + trip_dur
    total_del = trsz["traffic_delay"] + wsz["weather_delay"] + min(2, n_stops // 10)
    hist_hr   = HOUR_AVG.get(hour, 30.0)

    # service_date is treated as a NUMERIC feature by the model (feature_idx=0).
    # Pass it as the proleptic Gregorian ordinal (an integer) so CatBoost can
    # convert it to float without raising "Cannot convert '2026-06-27' to float".
    service_date_ordinal = pd.Timestamp("2026-06-27").toordinal()  # e.g. 738697

    raw: Dict[str, Any] = {
        "service_date":              service_date_ordinal,
        "route_id":                  route["route_id"],
        "route_short_name":          route["route_short_name"],
        "route_type":                route["route_type"],
        "service_id":                f"SVC-{route['route_id']}",
        "trip_id":                   f"TRIP-{route['route_id']}-{hour:02d}",
        "shape_id":                  f"SHAPE-{route['route_id']}",
        "direction_id":              0,
        "stop_id":                   f"STOP-{route['route_id']}-MID",
        "stop_name":                 f"Route {route['route_id']} Midpoint",
        "stop_sequence":             max(1, n_stops // 2),
        "stop_lat":                  13.0827 + (abs(hash(route["route_id"])) % 100) * 0.001,
        "stop_lon":                  80.2707 + (abs(hash(route["route_id"])) % 100) * 0.001,
        "terminal_stop_flag":        0,
        "major_interchange_flag":    1 if route["is_hub"] else 0,
        "area_type":                 route["area_type"],
        "cumulative_distance":       round(length_km / 2, 2),
        "remaining_distance":        round(length_km / 2, 2),
        "number_of_stops":           n_stops,
        "remaining_stops":           max(1, n_stops // 2),
        "route_length_km":           round(length_km, 2),
        "scheduled_trip_duration":   trip_dur,
        "trip_start_time":           t_start,
        "trip_end_time":             t_end,
        "hour":                      hour,
        "minute":                    0,
        "time_slot":                 tsz["time_slot"],
        "day_of_week":               "Monday",
        "weekday_weekend":           "Weekday",
        "month":                     6,
        "holiday_flag":              0,
        "peak_hour_flag":            tsz["peak_hour_flag"],
        "weather_condition":         wsz["weather_condition"],
        "temperature":               wsz["temperature"],
        "rainfall_flag":             wsz["rainfall_flag"],
        "congestion_index":          trsz["congestion_index"],
        "traffic_level":             trsz["traffic_level"],
        "average_speed":             trsz["average_speed"],
        "traffic_delay":             trsz["traffic_delay"],
        "weather_delay":             wsz["weather_delay"],
        "boarding_delay":            min(3, n_stops // 15),
        "total_delay":               total_del,
        "headway_minutes":           headway,
        "service_frequency_category": svc_freq,
        "historical_route_average":  hist["hist_route"],
        "historical_stop_average":   hist["hist_stop"],
        "historical_hour_average":   hist_hr,
        "historical_peak_average":   hist["hist_peak"],
        "historical_weekend_average":hist["hist_wknd"],
        "route_popularity_score":    hist["pop"],
        "vehicle_capacity":          60,
        # Leakage features still in model schema — set to neutral midpoints,
        # NOT to target-derived values, to avoid answer leakage.
        "boarding_count":    max(1, int(hist["hist_stop"] * 0.40)),
        "alighting_count":   max(1, int(hist["hist_stop"] * 0.35)),
        "onboard_passengers":max(1, int(hist["hist_stop"] * 0.50)),
        "occupancy_ratio":   0.40,
        "load_factor":       0.40,
        "demand_class":      "Medium",
    }

    ordered = {f: [raw.get(f, 0)] for f in feature_names}
    df = pd.DataFrame(ordered)
    for col in cat_features:
        if col in df.columns:
            df[col] = df[col].astype(str)
    return df


# =============================================================================
# PREDICTION HELPERS
# =============================================================================

def predict_demand(model: CatBoostRegressor, df: pd.DataFrame, cat_features: List[str]) -> int:
    try:
        pool = Pool(data=df, cat_features=cat_features)
        raw  = model.predict(pool)[0]
        return max(0, int(round(float(raw))))
    except Exception as exc:
        log.warning("Prediction error: %s", exc)
        return -1


def buses_required(passengers: int, capacity: int = 60) -> int:
    if passengers <= 0:
        return 1
    return math.ceil(passengers / capacity)


def confidence_from_metrics(metrics: Dict) -> float:
    r2   = metrics.get("R2",   0.97)
    rmse = metrics.get("RMSE", 3.0)
    base = min(0.99, max(0.70, r2))
    if rmse < 2.0:
        base += 0.02
    elif rmse > 5.0:
        base -= 0.05
    return round(min(0.99, max(0.60, base)), 3)


# =============================================================================
# VALIDATION CHECKS
# =============================================================================

def run_validation_checks(results: List[Dict]) -> Dict:
    demands = [r["predicted_demand"] for r in results if r["predicted_demand"] >= 0]
    if not demands:
        return {"stats": {}, "checks": {"error": {"passed": False, "detail": "No valid predictions."}}}

    d = np.array(demands, dtype=float)
    d_mean = float(d.mean())
    d_std  = float(d.std())
    cv     = (d_std / d_mean * 100) if d_mean > 0 else 0.0

    stats = {
        "demand_min":    round(float(d.min()), 2),
        "demand_max":    round(float(d.max()), 2),
        "demand_mean":   round(d_mean, 2),
        "demand_std":    round(d_std,  2),
        "demand_cv_pct": round(cv, 2),
        "n_predictions": len(demands),
    }

    checks: Dict[str, Dict] = {}

    # 1. Non-constant predictor
    checks["non_constant_predictor"] = {
        "passed": cv > 5.0,
        "cv_pct": round(cv, 2),
        "std":    round(d_std, 2),
        "detail": f"CV={cv:.2f}% (threshold >5%)",
    }

    # 2. Peak > Off-peak
    pk  = [r["predicted_demand"] for r in results if r["hour"] in (8, 18)  and r["predicted_demand"] >= 0]
    op  = [r["predicted_demand"] for r in results if r["hour"] in (14, 22) and r["predicted_demand"] >= 0]
    pm  = float(np.mean(pk)) if pk else 0.0
    om  = float(np.mean(op)) if op else 0.0
    checks["peak_exceeds_offpeak"] = {
        "passed":       pm > om,
        "peak_mean":    round(pm, 2),
        "offpeak_mean": round(om, 2),
        "ratio":        round(pm / om, 3) if om > 0 else 0.0,
        "detail":       f"Peak={pm:.1f} vs Off-peak={om:.1f}",
    }

    # 3. Traffic effect
    hv = [r["predicted_demand"] for r in results if r["traffic"] == "Heavy" and r["predicted_demand"] >= 0]
    lv = [r["predicted_demand"] for r in results if r["traffic"] == "Low"   and r["predicted_demand"] >= 0]
    hm = float(np.mean(hv)) if hv else 0.0
    lm = float(np.mean(lv)) if lv else 0.0
    tfx = abs(hm - lm) / (lm + 1e-9) * 100
    checks["traffic_affects_demand"] = {
        "passed":      tfx > 1.0,
        "heavy_mean":  round(hm, 2),
        "low_mean":    round(lm, 2),
        "effect_pct":  round(tfx, 2),
        "detail":      f"Traffic effect={tfx:.2f}% (Low={lm:.1f}, Heavy={hm:.1f})",
    }

    # 4. Weather effect
    cl = [r["predicted_demand"] for r in results if r["weather"] == "Clear" and r["predicted_demand"] >= 0]
    rn = [r["predicted_demand"] for r in results if r["weather"] == "Rainy" and r["predicted_demand"] >= 0]
    cm = float(np.mean(cl)) if cl else 0.0
    rm = float(np.mean(rn)) if rn else 0.0
    wfx = abs(rm - cm) / (cm + 1e-9) * 100
    checks["weather_affects_demand"] = {
        "passed":      wfx > 0.5,
        "clear_mean":  round(cm, 2),
        "rainy_mean":  round(rm, 2),
        "effect_pct":  round(wfx, 2),
        "detail":      f"Weather effect={wfx:.2f}% (Clear={cm:.1f}, Rainy={rm:.1f})",
    }

    # 5. Long vs Short route difference
    lng = [r["predicted_demand"] for r in results if r.get("route_category") == "long"  and r["predicted_demand"] >= 0]
    sht = [r["predicted_demand"] for r in results if r.get("route_category") == "short" and r["predicted_demand"] >= 0]
    lnm = float(np.mean(lng)) if lng else 0.0
    shm = float(np.mean(sht)) if sht else 0.0
    rfx = abs(lnm - shm) / (shm + 1e-9) * 100
    checks["long_vs_short_differ"] = {
        "passed":      rfx > 5.0,
        "long_mean":   round(lnm, 2),
        "short_mean":  round(shm, 2),
        "effect_pct":  round(rfx, 2),
        "detail":      f"Route-length effect={rfx:.2f}% (Short={shm:.1f}, Long={lnm:.1f})",
    }

    # 6. Sanity range [0, 500]
    sanity = bool(float(d.min()) >= 0 and float(d.max()) <= 500)
    checks["demand_range_sanity"] = {
        "passed": sanity,
        "min":    round(float(d.min()), 2),
        "max":    round(float(d.max()), 2),
        "detail": f"All values in [0,500]: {sanity}",
    }

    # 7. No catastrophic failures
    n_fail = sum(1 for r in results if r["predicted_demand"] < 0)
    checks["no_catastrophic_failures"] = {
        "passed":   n_fail == 0,
        "failures": n_fail,
        "total":    len(results),
        "detail":   f"{n_fail}/{len(results)} predictions failed",
    }

    return {"stats": stats, "checks": checks}


# =============================================================================
# VERDICT
# =============================================================================

def determine_verdict(validation: Dict) -> Tuple[str, str, Dict]:
    checks    = validation.get("checks", {})
    stats     = validation.get("stats",  {})
    valid_c   = {k: v for k, v in checks.items() if isinstance(v, dict) and "passed" in v}
    n_pass    = sum(1 for v in valid_c.values() if v["passed"])
    n_total   = len(valid_c)
    pass_rate = n_pass / n_total if n_total > 0 else 0.0
    cv        = stats.get("demand_cv_pct", 0.0)

    critical = ["non_constant_predictor", "peak_exceeds_offpeak",
                "no_catastrophic_failures", "demand_range_sanity"]
    crit_ok = all(valid_c.get(c, {}).get("passed", False) for c in critical)

    if crit_ok and pass_rate >= 0.85 and cv >= 10.0:
        grade = "A"
        label = "Production Ready"
        desc  = ("All critical checks passed. Demand variance is healthy (CV>=10%). "
                 "Model shows strong sensitivity to time-of-day, weather, traffic, and "
                 "route length. Safe to deploy to production.")
    elif crit_ok and pass_rate >= 0.60 and cv >= 5.0:
        grade = "B"
        label = "Acceptable for Pilot"
        desc  = ("Critical checks passed but some non-critical checks failed, or variance "
                 "is moderate (5%<=CV<10%). Deploy in shadow mode alongside existing "
                 "system, collect 4 weeks of production actuals, then re-run this audit.")
    else:
        grade = "C"
        label = "Requires Dataset Rebuild"
        desc  = ("One or more critical checks failed, or the model behaves as a near-constant "
                 "predictor (CV<5%). Expand training dataset diversity, fix remaining feature "
                 "leakage, and retrain from scratch.")

    recs = _build_recommendations(valid_c, stats, grade)
    summary = {
        "grade":                  grade,
        "label":                  label,
        "description":            desc,
        "checks_passed":          n_pass,
        "checks_total":           n_total,
        "pass_rate_pct":          round(pass_rate * 100, 1),
        "demand_cv_pct":          round(cv, 2),
        "critical_checks_passed": crit_ok,
        "recommendations":        recs,
    }
    return grade, label, summary


def _build_recommendations(checks: Dict, stats: Dict, grade: str) -> List[str]:
    recs: List[str] = []
    if not checks.get("non_constant_predictor", {}).get("passed"):
        recs.append("[CRITICAL] Near-constant predictor (CV<5%). Diversify training data across time slots and route categories.")
    if not checks.get("peak_exceeds_offpeak", {}).get("passed"):
        recs.append("[WARNING] Peak demand not exceeding off-peak. Verify peak_hour_flag and time_slot have sufficient variance in training data.")
    if not checks.get("traffic_affects_demand", {}).get("passed"):
        recs.append("[INFO] Traffic has minimal impact. Add congestion x historical interaction terms or broaden traffic data coverage.")
    if not checks.get("weather_affects_demand", {}).get("passed"):
        recs.append("[INFO] Weather has minimal impact. Ensure rainfall_flag and weather_condition have sufficient variance in training data.")
    if not checks.get("long_vs_short_differ", {}).get("passed"):
        recs.append("[WARNING] Long and short routes produce similar demand. Ensure route_length_km and historical_route_average vary meaningfully.")
    if not checks.get("demand_range_sanity", {}).get("passed"):
        recs.append("[CAUTION] Demand predictions outside [0,500]. Add output clipping and review training data outliers.")
    if not checks.get("no_catastrophic_failures", {}).get("passed"):
        recs.append("[CRITICAL] Prediction failures detected. Investigate feature schema mismatches between training config and inference.")
    if grade == "A":
        recs.append("[NEXT] Automate weekly validation runs post-deployment. Re-evaluate after 3 months.")
    elif grade == "B":
        recs.append("[NEXT] Shadow-mode deployment. Re-run audit after 4 weeks of production data collection.")
    else:
        recs.append("[NEXT] Rebuild dataset with broader scenario coverage, then retrain.")
    return recs


# =============================================================================
# SAVE REPORTS
# =============================================================================

def save_validation_report(results: List[Dict], validation: Dict,
                            routes: List[Dict], training_metrics: Dict) -> None:
    report = {
        "audit_metadata": {
            "timestamp":         datetime.now().isoformat(),
            "model_path":        str(MODEL_PATH),
            "total_routes":      len(routes),
            "total_predictions": len(results),
            "scenarios": {
                "time":    list(TIME_SCENARIOS.keys()),
                "weather": list(WEATHER_SCENARIOS.keys()),
                "traffic": list(TRAFFIC_SCENARIOS.keys()),
            },
        },
        "training_metrics":        training_metrics,
        "demand_statistics":       validation.get("stats", {}),
        "physical_realism_checks": validation.get("checks", {}),
        "routes_tested":           routes,
        "predictions":             results,
    }
    with open(VALIDATION_REPORT, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, ensure_ascii=False, default=str)
    log.info("Validation report  ->  %s", VALIDATION_REPORT)


def save_readiness_report(grade: str, label: str, summary: Dict) -> None:
    action = {
        "A": "APPROVED  — deploy to production",
        "B": "PILOT     — shadow-mode deployment",
        "C": "BLOCKED   — retrain required",
    }.get(grade, "UNKNOWN")

    report = {
        "generated_at": datetime.now().isoformat(),
        "model_path":   str(MODEL_PATH),
        "verdict": {
            "grade":  grade,
            "label":  label,
            "action": action,
        },
        **summary,
    }
    with open(READINESS_REPORT, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, ensure_ascii=False, default=str)
    log.info("Readiness report   ->  %s", READINESS_REPORT)


# =============================================================================
# DISPLAY HELPERS
# =============================================================================

def banner(text: str, width: int = 64) -> None:
    log.info("=" * width)
    log.info(text.center(width))
    log.info("=" * width)


def print_check_table(checks: Dict) -> None:
    log.info("%-42s %-6s  %s", "CHECK", "RESULT", "DETAIL")
    log.info("-" * 90)
    for name, info in checks.items():
        if not isinstance(info, dict) or "passed" not in info:
            continue
        status = "PASS" if info["passed"] else "FAIL"
        log.info("%-42s %-6s  %s", name, status, info.get("detail", ""))


def print_scenario_matrix(results: List[Dict]) -> None:
    log.info("")
    log.info("%-22s %-8s %-8s  %s", "TIME SCENARIO", "WEATHER", "TRAFFIC", "AVG DEMAND")
    log.info("-" * 70)
    for tname, wname, trname in iproduct(TIME_SCENARIOS, WEATHER_SCENARIOS, TRAFFIC_SCENARIOS):
        vals = [
            r["predicted_demand"] for r in results
            if r["time_scenario"] == tname
            and r["weather"]       == wname
            and r["traffic"]       == trname
            and r["predicted_demand"] >= 0
        ]
        avg = float(np.mean(vals)) if vals else float("nan")
        log.info("%-22s %-8s %-8s  %.1f", tname, wname, trname, avg)


# =============================================================================
# MAIN
# =============================================================================

def main() -> None:
    banner("POST-RETRAIN VALIDATION AUDIT")
    t0 = datetime.now()

    # 1. Load model
    model, model_cfg, training_metrics = load_model_artifacts()
    feature_names = model_cfg.get("feature_names", list(model.feature_names_))
    cat_features  = model_cfg.get("categorical_features", [])
    confidence    = confidence_from_metrics(training_metrics)
    log.info("Schema: %d features | %d categoricals | confidence=%.3f",
             len(feature_names), len(cat_features), confidence)

    # 2. Select routes from GTFS
    banner("SELECTING ROUTES FROM GTFS")
    route_df = compute_route_lengths_from_gtfs()
    routes   = select_routes(route_df)
    log.info("Routes selected: %d", len(routes))

    # 3. Run all scenario predictions
    banner("RUNNING SCENARIO PREDICTIONS")
    results: List[Dict] = []
    total = len(routes) * len(TIME_SCENARIOS) * len(WEATHER_SCENARIOS) * len(TRAFFIC_SCENARIOS)
    log.info("Total combinations: %d", total)
    done = 0

    for route in routes:
        for time_name, time_cfg in TIME_SCENARIOS.items():
            for weather_name in WEATHER_SCENARIOS:
                for traffic_name in TRAFFIC_SCENARIOS:
                    df_row = build_feature_row(
                        route, time_name, weather_name, traffic_name,
                        feature_names, cat_features,
                    )
                    demand = predict_demand(model, df_row, cat_features)
                    results.append({
                        "route_id":         route["route_id"],
                        "route_short_name": route["route_short_name"],
                        "route_category":   route["category"],
                        "route_length_km":  route["estimated_length_km"],
                        "avg_stops":        route["avg_stops"],
                        "time_scenario":    time_name,
                        "hour":             time_cfg["hour"],
                        "weather":          weather_name,
                        "traffic":          traffic_name,
                        "predicted_demand": demand,
                        "confidence":       confidence,
                        "buses_required":   buses_required(demand),
                    })
                    done += 1
                    if done % 100 == 0 or done == total:
                        log.info("  Progress: %d / %d  (%.1f%%)", done, total, done / total * 100)

    log.info("All predictions complete: %d results", len(results))

    # 4. Statistics
    banner("DEMAND STATISTICS")
    valid_d = [r["predicted_demand"] for r in results if r["predicted_demand"] >= 0]
    if not valid_d:
        log.error("CRITICAL: All %d predictions returned -1 (total failure). "
                  "Check feature schema — most likely a numeric feature is being "
                  "passed as a non-numeric type.", len(results))
        sys.exit(1)
    d = np.array(valid_d, dtype=float)
    log.info("  Demand Min    : %d",     int(d.min()))
    log.info("  Demand Max    : %d",     int(d.max()))
    log.info("  Demand Mean   : %.2f",   d.mean())
    log.info("  Demand Std Dev: %.2f",   d.std())
    log.info("  Demand CV     : %.2f%%", d.std() / d.mean() * 100 if d.mean() > 0 else 0.0)
    log.info("  Valid preds   : %d / %d", len(valid_d), len(results))

    # 5. Scenario matrix
    banner("SCENARIO DEMAND MATRIX")
    print_scenario_matrix(results)

    # 6. Physical realism checks
    banner("PHYSICAL REALISM CHECKS")
    validation = run_validation_checks(results)
    print_check_table(validation.get("checks", {}))

    # 7. Verdict
    grade, label, summary = determine_verdict(validation)
    banner(f"VERDICT:  {grade}  -  {label}")
    log.info("Checks Passed : %d / %d  (%.1f%%)",
             summary["checks_passed"], summary["checks_total"], summary["pass_rate_pct"])
    log.info("Demand CV     : %.2f%%", summary["demand_cv_pct"])
    log.info("Description   : %s", summary["description"])
    log.info("Recommendations:")
    for rec in summary["recommendations"]:
        log.info("  * %s", rec)

    # 8. Save reports
    banner("SAVING REPORTS")
    save_validation_report(results, validation, routes, training_metrics)
    save_readiness_report(grade, label, summary)

    elapsed = (datetime.now() - t0).total_seconds()
    banner(f"AUDIT COMPLETE  -  {elapsed:.1f}s")
    log.info("Output files:")
    log.info("  %s", VALIDATION_REPORT)
    log.info("  %s", READINESS_REPORT)


if __name__ == "__main__":
    main()
