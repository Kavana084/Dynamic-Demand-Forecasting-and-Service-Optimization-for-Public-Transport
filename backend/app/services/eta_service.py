"""
ETA Service  —  Single Source of Truth for ETA Calculation
----------------------------------------------------------
Replaces the deleted eta_prediction_service.py completely.

Inputs  : total_distance_km, predicted_demand, bus_cap,
          traffic_state, weather_condition, peak_status
Outputs : eta_minutes (int), delay_minutes (int),
          occupancy (int 0-100), eta_confidence (float 0-1)
"""

import datetime
import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Multiplier Tables
# ---------------------------------------------------------------------------
TRAFFIC_MULT: dict[str, float] = {
    "Low":    1.00,
    "Medium": 1.15,
    "High":   1.35,
    "Heavy":  1.60,
}

WEATHER_MULT: dict[str, float] = {
    "Clear":  1.00,
    "Cloudy": 1.05,
    "Rainy":  1.22,
    "Storm":  1.50,
}

OCCUPANCY_MULT: dict[str, float] = {
    "low":    1.00,   # < 50 %
    "medium": 1.08,   # 50-80 %
    "high":   1.20,   # > 80 %
}

PEAK_MULT: dict[str, float] = {
    "normal":       1.00,
    "morning_peak": 1.12,
    "evening_peak": 1.15,
    "surge":        1.30,
}

AVG_SPEED_KMPH = 20.0   # Realistic urban bus speed


def _occupancy_tier(occupancy_ratio: float) -> str:
    if occupancy_ratio < 0.50:
        return "low"
    if occupancy_ratio <= 0.80:
        return "medium"
    return "high"


def _boarding_delay(occupancy_ratio: float) -> float:
    """Extra boarding/alighting time when bus is crowded."""
    if occupancy_ratio > 0.85:
        return (occupancy_ratio - 0.85) * 10.0
    return 0.0


def _weather_dwell_penalty(weather: str) -> float:
    """Additional dwell time in adverse weather (passengers move slower)."""
    return {"Clear": 0.0, "Cloudy": 0.5, "Rainy": 2.0, "Storm": 4.0}.get(weather, 0.0)


def calculate_eta(
    total_distance_km: float,
    predicted_demand:  int,
    bus_cap:           int,
    traffic_state:     str = "Medium",
    weather_condition: str = "Clear",
    peak_status:       str = "normal",
) -> dict:
    """
    Physics-based ETA calculation with layered impact factors.

    Parameters
    ----------
    total_distance_km : Remaining route distance (not full route).
    predicted_demand  : Expected passengers on this route.
    bus_cap           : Bus seated+standing capacity.
    traffic_state     : Low | Medium | High | Heavy
    weather_condition : Clear | Cloudy | Rainy | Storm
    peak_status       : normal | morning_peak | evening_peak | surge

    Returns
    -------
    {
        "eta_minutes"   : int,
        "delay_minutes" : int,
        "occupancy"     : int,    # 0-100
        "eta_confidence": float   # 0.0-1.0
    }
    """
    # 1. Gather multipliers
    traffic_m  = TRAFFIC_MULT.get(traffic_state,     1.15)
    weather_m  = WEATHER_MULT.get(weather_condition, 1.00)
    peak_m     = PEAK_MULT.get(peak_status,          1.00)

    # 2. Occupancy ratio + tier
    occupancy_ratio = min(predicted_demand / max(bus_cap, 1), 1.5)
    occ_tier        = _occupancy_tier(occupancy_ratio)
    occ_m           = OCCUPANCY_MULT[occ_tier]

    # 3. Base ETA (physics)
    base_eta = (total_distance_km / AVG_SPEED_KMPH) * 60.0

    # 4. Apply multipliers
    adjusted_eta = base_eta * traffic_m * weather_m * occ_m * peak_m

    # 5. Delays: boarding + weather dwell
    boarding = _boarding_delay(occupancy_ratio)
    dwell    = _weather_dwell_penalty(weather_condition)

    eta_minutes   = max(1, int(adjusted_eta + boarding + dwell))
    delay_minutes = max(0, eta_minutes - int(base_eta))
    occupancy     = min(100, int(occupancy_ratio * 100))

    # 6. Confidence calculation
    confidence = _calculate_confidence(traffic_state, weather_condition, peak_status)

    result = {
        "eta_minutes"   : eta_minutes,
        "delay_minutes" : delay_minutes,
        "occupancy"     : occupancy,
        "eta_confidence": confidence,
    }

    logger.debug(
        f"ETA calc | dist={total_distance_km}km | traffic={traffic_state} | "
        f"weather={weather_condition} | peak={peak_status} | "
        f"eta={eta_minutes}m | conf={confidence}"
    )
    return result


def _calculate_confidence(
    traffic_state:     str,
    weather_condition: str,
    peak_status:       str,
) -> float:
    """
    ETA confidence degrades with:
      - Storm weather
      - Heavy traffic
      - Surge peak conditions
    """
    confidence = 0.98

    # Weather impact
    if weather_condition == "Storm":
        confidence -= 0.15
    elif weather_condition == "Rainy":
        confidence -= 0.07
    elif weather_condition == "Cloudy":
        confidence -= 0.02

    # Traffic impact
    if traffic_state == "Heavy":
        confidence -= 0.10
    elif traffic_state == "High":
        confidence -= 0.05
    elif traffic_state == "Medium":
        confidence -= 0.02

    # Peak-hour uncertainty
    if peak_status == "surge":
        confidence -= 0.06
    elif peak_status in ("morning_peak", "evening_peak"):
        confidence -= 0.03

    # Hour-of-day (late night / early morning = less data)
    current_hour = datetime.datetime.now().hour
    if current_hour < 6 or current_hour > 22:
        confidence -= 0.05

    return round(max(0.60, confidence), 2)
