"""
schedule_engine.py
==================
City-Level Demand-Based Schedule Frequency Engine

This module computes BUS FREQUENCY PER ROUTE (buses/hour) based on:
  - Aggregated passenger demand (ML prediction)
  - Peak / off-peak hour detection
  - Real-time traffic conditions
  - Real-time weather conditions

IMPORTANT: This is a BATCH system — it runs every N minutes via APScheduler.
           It does NOT run per-request. It does NOT assign buses to passengers.
           It behaves like a City Transit Authority scheduling engine.

Output is stored in the app_cache under key: 'schedule_status'
API endpoint /api/schedule_status reads from this cache.
"""

import datetime
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

# ── Frequency tiers ───────────────────────────────────────────────────────────
# These map demand + conditions to a service frequency level.
#
#   HIGH   → 6–8 buses/hour  → headway ~8–10 min   (peak / heavy demand)
#   MEDIUM → 4–6 buses/hour  → headway ~10–15 min  (normal operations)
#   LOW    → 2–3 buses/hour  → headway ~20–30 min  (off-peak / low demand)

FREQUENCY_TIERS: Dict[str, Dict[str, Any]] = {
    "HIGH": {
        "label": "High Frequency",
        "buses_per_hour": 8,
        "headway_minutes": 8,
        "color": "green",
    },
    "MEDIUM": {
        "label": "Normal Frequency",
        "buses_per_hour": 5,
        "headway_minutes": 12,
        "color": "blue",
    },
    "LOW": {
        "label": "Reduced Frequency",
        "buses_per_hour": 3,
        "headway_minutes": 20,
        "color": "orange",
    },
    "MINIMAL": {
        "label": "Minimal Service",
        "buses_per_hour": 2,
        "headway_minutes": 30,
        "color": "red",
    },
}

# Peak hours — morning and evening rush
PEAK_HOURS = {7, 8, 9, 10, 17, 18, 19, 20}

# Demand thresholds for tier selection
HIGH_DEMAND_THRESHOLD = 80   # passengers predicted
LOW_DEMAND_THRESHOLD  = 30   # passengers predicted


def _is_peak_hour(hour: int) -> bool:
    return hour in PEAK_HOURS


def _get_condition_multiplier(traffic: str, weather: str) -> float:
    """
    Returns a demand-pressure multiplier based on external conditions.
    Higher multiplier = more pressure = higher frequency needed.
    """
    t = (traffic or "").strip().title()
    w = (weather or "").strip().split(",")[0].strip().title()

    traffic_factor = {
        "Low":    1.0,
        "Medium": 1.1,
        "High":   1.25,
        "Heavy":  1.4,
    }.get(t, 1.0)

    weather_factor = {
        "Clear":  1.0,
        "Cloudy": 1.05,
        "Rainy":  1.20,
    }.get(w, 1.0)

    return traffic_factor * weather_factor


def compute_route_frequency(
    route_id: str,
    passenger_demand: int,
    hour: int,
    traffic: str = "Medium",
    weather: str = "Clear",
) -> Dict[str, Any]:
    """
    Compute service frequency tier for a single route.

    Args:
        route_id:         The route identifier.
        passenger_demand: ML-predicted passenger demand for this hour.
        hour:             Current hour (0–23).
        traffic:          Traffic condition string ("Low"|"Medium"|"High"|"Heavy").
        weather:          Weather condition string ("Clear"|"Cloudy"|"Rainy" …).

    Returns:
        Dict with keys:
            route_id, frequency_tier, label, buses_per_hour,
            headway_minutes, color, reason, is_peak
    """
    is_peak     = _is_peak_hour(hour)
    multiplier  = _get_condition_multiplier(traffic, weather)
    adjusted_demand = int(passenger_demand * multiplier)

    # ── Tier selection logic ──────────────────────────────────────────────────
    #   Rule 1: Peak hours → at least MEDIUM
    #   Rule 2: High adjusted demand → HIGH
    #   Rule 3: Bad weather OR heavy traffic → step up one tier
    #   Rule 4: Low demand + off-peak → LOW or MINIMAL

    reasons: List[str] = []

    if adjusted_demand >= HIGH_DEMAND_THRESHOLD:
        tier = "HIGH"
        reasons.append(f"high demand ({adjusted_demand} pax predicted)")
    elif is_peak:
        tier = "HIGH"
        reasons.append("peak hours")
    elif adjusted_demand >= LOW_DEMAND_THRESHOLD:
        tier = "MEDIUM"
        reasons.append(f"moderate demand ({adjusted_demand} pax)")
    else:
        tier = "LOW"
        reasons.append(f"low demand ({adjusted_demand} pax)")

    # Weather / traffic bump
    w_label = (weather or "").split(",")[0].strip().title()
    t_label = (traffic or "").strip().title()

    if w_label == "Rainy" and tier == "LOW":
        tier = "MEDIUM"
        reasons.append("rain increases ridership")
    if t_label in ("High", "Heavy") and tier == "MEDIUM":
        tier = "HIGH"
        reasons.append("heavy traffic → increase frequency")

    # Midnight / very early morning
    if hour < 5 or hour >= 23:
        if tier != "HIGH":
            tier = "MINIMAL"
            reasons.append("late-night / early-morning service window")

    tier_data = FREQUENCY_TIERS[tier]

    # Compute next arrival times from now
    now          = datetime.datetime.now()
    headway      = tier_data["headway_minutes"]
    next_arrivals = [
        {
            "bus_number": i,
            "arrival_time": (now + datetime.timedelta(minutes=headway * i)).strftime("%I:%M %p")
        }
        for i in range(1, 5)   # next 4 buses
    ]

    return {
        "route_id":        route_id,
        "frequency_tier":  tier,
        "label":           tier_data["label"],
        "buses_per_hour":  tier_data["buses_per_hour"],
        "headway_minutes": headway,
        "color":           tier_data["color"],
        "is_peak":         is_peak,
        "adjusted_demand": adjusted_demand,
        "reason":          "; ".join(reasons),
        "next_arrivals":   next_arrivals,
    }


def update_schedule_engine(app_state=None, app_cache=None) -> Dict[str, Any]:
    """
    Batch schedule engine — aggregates demand + conditions for ALL routes
    and updates the 'schedule_status' cache key.

    Called by APScheduler every 10 minutes.
    NOT called per user request.

    Args:
        app_state:  FastAPI app.state (contains prediction_service, dataset)
        app_cache:  The app cache instance

    Returns:
        Dict with 'routes' list and 'updated_at' timestamp.
    """
    if app_cache is None or app_state is None:
        logger.warning("update_schedule_engine: missing app_state or app_cache — skipping.")
        return {}

    svc     = getattr(app_state, "prediction_service", None)
    dataset = getattr(app_state, "dataset", None)

    if svc is None or svc.model is None or dataset is None:
        logger.warning("update_schedule_engine: prediction service or dataset not ready — skipping.")
        return {}

    hour    = datetime.datetime.now().hour
    weather = app_cache.get("weather") or "Clear, 28°C"
    traffic = app_cache.get("traffic") or "Medium"

    unique_routes = dataset["route_id"].unique().tolist()
    # Cap at 30 routes for performance
    if len(unique_routes) > 30:
        unique_routes = unique_routes[:30]

    route_schedules: List[Dict[str, Any]] = []

    for r_id in unique_routes:
        try:
            demand = svc.predict_demand(
                route_id=str(r_id),
                hour=hour,
                weather_condition=weather.split(",")[0].strip(),
                traffic=traffic,
            )
            freq = compute_route_frequency(
                route_id=str(r_id),
                passenger_demand=int(demand),
                hour=hour,
                traffic=traffic,
                weather=weather,
            )
            route_schedules.append(freq)
        except Exception as e:
            logger.error(f"update_schedule_engine: error for route {r_id}: {e}")

    result = {
        "routes":      route_schedules,
        "updated_at":  datetime.datetime.now().isoformat(),
        "conditions":  {"weather": weather, "traffic": traffic, "hour": hour},
        "peak_active": _is_peak_hour(hour),
        "total_routes_scheduled": len(route_schedules),
    }

    app_cache.set("schedule_status", result, ttl_seconds=900)  # 15-min TTL
    logger.info(
        f"[ScheduleEngine] Updated {len(route_schedules)} routes | "
        f"hour={hour} | traffic={traffic} | weather={weather.split(',')[0]}"
    )
    return result
