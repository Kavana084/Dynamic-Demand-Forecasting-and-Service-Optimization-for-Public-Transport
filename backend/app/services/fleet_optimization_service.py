"""
fleet_optimization_service.py — Per-Route Fleet Allocation Engine
==================================================================
Improvements:
  1. compute_demand_metrics() is the SINGLE source of truth for all
     dashboard metric fields (occupancy, demand_level, comfort, fleet rec).
  2. Single-route optimize() remains for per-trip fleet checks.
  3. New batch_optimize() processes a Dict[route_id -> demand] and returns
     per-route breakdown with required_fleet, fleet_gap, utilization,
     unmet_demand — all computed dynamically, no hardcoded values.
  4. Dynamic recommendations generated from fleet_gap and utilization.
"""

import math
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# Total available buses in the depot — can be overridden per call
DEFAULT_FLEET_SIZE           = 20
DEFAULT_FLEET_SIZE_PER_ROUTE = 5    # buses available per individual route in batch mode
DEFAULT_BUS_CAPACITY         = 60
DEFAULT_LOW_DEMAND_THRESHOLD = 30

# ---------------------------------------------------------------------------
# Demand thresholds — configurable at runtime.
# Override by calling: set_demand_thresholds({"Low": (0,99), ...})
# or by setting the DEMAND_THRESHOLDS dict directly before startup.
# ---------------------------------------------------------------------------
DEMAND_THRESHOLDS: Dict[str, tuple] = {
    "Low":      (0,   149),
    "Moderate": (150, 399),
    "High":     (400, 699),
    "Critical": (700, float("inf")),
}

# Crowd level occupancy breakpoints — can be overridden the same way.
CROWD_THRESHOLDS: Dict[str, float] = {
    "Low":       40.0,   # occ < 40%  -> Low
    "Moderate":  70.0,   # occ < 70%  -> Moderate
    "High":      90.0,   # occ < 90%  -> High
    # else                            -> Very High
}

# Maximum acceptable wait time (headway) by service period.
# Drives frequency-based bus sizing inside compute_demand_metrics().
# Peak: ≤10 min headway; Off-peak: ≤15 min headway.
# Override via set_wait_thresholds() or directly before startup.
MAX_ACCEPTABLE_WAIT_MINUTES: Dict[str, int] = {
    "peak":     10,
    "off_peak": 15,
}


def set_demand_thresholds(thresholds: Dict[str, tuple]) -> None:
    """Override DEMAND_THRESHOLDS at runtime (e.g., from a config file or DB)."""
    global DEMAND_THRESHOLDS
    DEMAND_THRESHOLDS = thresholds
    logger.info(f"DEMAND_THRESHOLDS updated: {thresholds}")


def set_crowd_thresholds(thresholds: Dict[str, float]) -> None:
    """Override CROWD_THRESHOLDS at runtime."""
    global CROWD_THRESHOLDS
    CROWD_THRESHOLDS = thresholds
    logger.info(f"CROWD_THRESHOLDS updated: {thresholds}")


def set_wait_thresholds(thresholds: Dict[str, int]) -> None:
    """Override MAX_ACCEPTABLE_WAIT_MINUTES at runtime."""
    global MAX_ACCEPTABLE_WAIT_MINUTES
    MAX_ACCEPTABLE_WAIT_MINUTES = thresholds
    logger.info(f"MAX_ACCEPTABLE_WAIT_MINUTES updated: {thresholds}")

SAFE_FLEET_PLAN = {
    "buses_required": 1,
    "frequency_adjustment": "stable",
    "utilization_score": 0.5,
    "load_factor": 0.5,
}


def compute_demand_metrics(
    route_predicted_passengers: int,
    journey_predicted_passengers: int,
    available_buses: int = DEFAULT_FLEET_SIZE,
    bus_capacity: int = DEFAULT_BUS_CAPACITY,
    is_peak: bool = False,
) -> dict:
    """
    THE single canonical function for all demand-derived dashboard fields.

    All dashboard cards, API responses, and service layers MUST call this
    function rather than recalculating occupancy, demand level, or comfort
    level independently.

    Parameters
    ----------
    route_predicted_passengers  : Total passengers expected on the entire route.
                                  Used exclusively for fleet allocation (required_buses,
                                  fleet_gap, recommendation). Never shown directly to
                                  the passenger.
    journey_predicted_passengers: Passengers expected on the user's selected segment
                                  (source -> destination). Shown on the passenger
                                  dashboard. Used for occupancy and crowd level.

    .. note:: APPROXIMATION WARNING
        When CatBoost is active, ``journey_predicted_passengers`` is the raw
        stop-level prediction (passengers at the *source stop*).  This is a
        reasonable proxy for journey-level demand but is NOT an exact count of
        passengers travelling the full selected segment.

        ``route_predicted_passengers`` is extrapolated from the stop-level
        prediction using a stop-count proportionality ratio
        (journey_stops / total_route_stops).  This ratio is a *temporary
        heuristic* and should be replaced with a trained segment-demand model
        once labelled segment-level data is available.

    available_buses : Buses currently allocated to this route (not total depot fleet).
    bus_capacity    : Seated + standing capacity of one bus.
    """
    if bus_capacity <= 0:
        logger.error("compute_demand_metrics: bus_capacity must be > 0; defaulting to 60.")
        bus_capacity = DEFAULT_BUS_CAPACITY

    route_predicted_passengers = max(0, int(route_predicted_passengers))
    journey_predicted_passengers = max(0, int(journey_predicted_passengers))
    available_buses      = max(0, int(available_buses))

    # ── Fleet allocation (based on route_predicted_passengers) ────────
    # Capacity-based sizing: how many buses needed to seat all passengers?
    capacity_required_buses = math.ceil(route_predicted_passengers / bus_capacity) if route_predicted_passengers > 0 else 0

    # Frequency-based sizing: how many buses needed to keep headway within
    # the acceptable wait-time target (ceil(60 / target_wait_minutes))?
    # target_wait is computed unconditionally so the log line below can always
    # reference it without hitting an UnboundLocalError on zero-demand routes.
    # frequency_required_buses collapses to 0 when there is no predicted demand —
    # there is no reason to schedule buses to meet a headway target on an empty route.
    target_wait = MAX_ACCEPTABLE_WAIT_MINUTES["peak"] if is_peak else MAX_ACCEPTABLE_WAIT_MINUTES["off_peak"]
    frequency_required_buses = math.ceil(60 / target_wait) if route_predicted_passengers > 0 else 0

    # Fleet allocation is based purely on passenger demand/capacity, not wait-time target.
    required_buses       = capacity_required_buses
    allocated_buses      = min(required_buses, available_buses)
    fleet_gap            = required_buses - available_buses   # negative = surplus
    additional_buses_needed = max(0, fleet_gap)

    # ── Allocation status ─────────────────────────────────────────────
    if fleet_gap > 0:
        allocation_status = "shortage"
    elif fleet_gap < 0:
        allocation_status = "surplus"
    else:
        allocation_status = "sufficient"

    # ── Occupancy (two measures based on journey demand) ──────────────
    # Ideal: exactly required_buses deployed — always <= 100 %.
    ideal_capacity          = max(1, required_buses * bus_capacity)
    ideal_occupancy_pct     = round((journey_predicted_passengers / ideal_capacity) * 100, 1) if journey_predicted_passengers > 0 else 0.0

    # Operational: what passengers actually experience given allocated fleet.
    # User requirement: Calculate occupancy using buses allocated to the route
    operational_capacity    = max(1, allocated_buses * bus_capacity) if allocated_buses > 0 else 1
    operational_occupancy_pct = round((journey_predicted_passengers / operational_capacity) * 100, 1) if journey_predicted_passengers > 0 else 0.0

    # ── Demand level (passenger-count thresholds, not occupancy) ──────
    demand_level = "Low"
    for level, (lo, hi) in DEMAND_THRESHOLDS.items():
        if lo <= journey_predicted_passengers <= hi:
            demand_level = level
            break

    # ── Crowd & comfort (operational occupancy) ───────────────────────
    # Driven by CROWD_THRESHOLDS dict — configurable via set_crowd_thresholds()
    occ = operational_occupancy_pct
    if occ < CROWD_THRESHOLDS["Low"]:
        crowd_level   = "Low"
        comfort_level = "High"
    elif occ < CROWD_THRESHOLDS["Moderate"]:
        crowd_level   = "Moderate"
        comfort_level = "Medium"
    elif occ < CROWD_THRESHOLDS["High"]:
        crowd_level   = "High"
        comfort_level = "Low"
    else:
        crowd_level   = "Very High"
        comfort_level = "Low"

    # ── Fleet recommendation — strictly consistent with fleet_gap ─────
    if additional_buses_needed == 0:
        fleet_recommendation = "No Additional Buses Required."
    elif additional_buses_needed <= 2:
        fleet_recommendation = (
            f"Allocate {additional_buses_needed} additional bus(es). "
            f"Demand of {route_predicted_passengers} passengers exceeds current fleet capacity."
        )
    else:
        fleet_recommendation = (
            f"Critical shortage — deploy {additional_buses_needed} additional buses immediately. "
            f"{route_predicted_passengers - available_buses * bus_capacity} passengers cannot be served."
        )

    result = {
        "route_predicted_passengers":   route_predicted_passengers,
        "journey_predicted_passengers": journey_predicted_passengers,
        "bus_capacity":              bus_capacity,
        "available_buses":           available_buses,
        "required_buses":            required_buses,
        "capacity_required_buses":   capacity_required_buses,
        "frequency_required_buses":  frequency_required_buses,
        "allocated_buses":           allocated_buses,
        "additional_buses_needed":   additional_buses_needed,
        "fleet_gap":                 fleet_gap,
        "ideal_occupancy_pct":       ideal_occupancy_pct,
        "operational_occupancy_pct": operational_occupancy_pct,
        "demand_level":              demand_level,
        "crowd_level":               crowd_level,
        "comfort_level":             comfort_level,
        "fleet_recommendation":      fleet_recommendation,
        "allocation_status":         allocation_status,
    }

    logger.info(
        f"DemandMetrics | route_pax={route_predicted_passengers} | journey_pax={journey_predicted_passengers} | cap={bus_capacity} | "
        f"avail={available_buses} | cap_req={capacity_required_buses} | freq_req={frequency_required_buses} | "
        f"req={required_buses} | alloc={allocated_buses} | is_peak={is_peak} | target_wait={target_wait}min | "
        f"ideal_occ={ideal_occupancy_pct}% | oper_occ={operational_occupancy_pct}% | "
        f"demand={demand_level} | comfort={comfort_level} | status={allocation_status}"
    )
    return result



def _safe_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _safe_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except Exception:
        return default


def compute_fleet_plan(route_data: dict, demand_data: dict) -> dict:
    """
    Pure deterministic post-processing decision layer.

    Consumes only already-computed route metrics, demand outputs, and occupancy
    data. It does not compute routes, access graphs, or invoke any ML logic.
    """
    if not isinstance(route_data, dict) or not isinstance(demand_data, dict):
        logger.info(
            "fleet_decision_layer",
            extra={
                "demand_input": None,
                "buses_required": SAFE_FLEET_PLAN["buses_required"],
                "utilization_score": SAFE_FLEET_PLAN["utilization_score"],
            },
        )
        return dict(SAFE_FLEET_PLAN)

    demand_input = demand_data.get("route_predicted_passengers")
    if demand_input is None:
        logger.info(
            "fleet_decision_layer",
            extra={
                "demand_input": None,
                "buses_required": SAFE_FLEET_PLAN["buses_required"],
                "utilization_score": SAFE_FLEET_PLAN["utilization_score"],
            },
        )
        return dict(SAFE_FLEET_PLAN)

    demand = max(0, _safe_int(demand_input, 0))
    if demand <= 0:
        logger.info(
            "fleet_decision_layer",
            extra={
                "demand_input": demand,
                "buses_required": SAFE_FLEET_PLAN["buses_required"],
                "utilization_score": SAFE_FLEET_PLAN["utilization_score"],
            },
        )
        return dict(SAFE_FLEET_PLAN)

    bus_capacity = max(
        1,
        _safe_int(
            route_data.get("bus_capacity", demand_data.get("bus_capacity", DEFAULT_BUS_CAPACITY)),
            DEFAULT_BUS_CAPACITY,
        ),
    )
    current_buses = max(
        1,
        _safe_int(
            route_data.get("current_buses", route_data.get("buses_per_hour", 1)),
            1,
        ),
    )
    occupancy = _safe_float(route_data.get("occupancy_percent"), -1.0)
    low_demand_threshold = max(
        1,
        _safe_int(demand_data.get("low_demand_threshold", DEFAULT_LOW_DEMAND_THRESHOLD), DEFAULT_LOW_DEMAND_THRESHOLD),
    )

    max_capacity = max(1, current_buses * bus_capacity)
    buses_required = max(1, math.ceil(demand / bus_capacity))
    recommended_capacity = max(1, buses_required * bus_capacity)
    utilization_score = round(demand / recommended_capacity, 3)

    if occupancy >= 0:
        load_factor = round(occupancy / 100.0, 3)
    else:
        load_factor = round(demand / max(bus_capacity, 1), 3)

    if occupancy > 80 or demand > max_capacity:
        frequency_adjustment = "increase"
    elif demand < low_demand_threshold:
        frequency_adjustment = "decrease"
    else:
        frequency_adjustment = "stable"

    result = {
        "buses_required": buses_required,
        "frequency_adjustment": frequency_adjustment,
        "utilization_score": utilization_score,
        "load_factor": load_factor,
    }

    logger.info(
        "fleet_decision_layer",
        extra={
            "demand_input": demand,
            "buses_required": buses_required,
            "utilization_score": utilization_score,
        },
    )
    logger.info(f"DEMAND_TRACE: fleet optimization recommended {buses_required} buses for demand {demand} (utilization: {utilization_score})")
    return result



class FleetOptimizationService:
    """
    Maps predicted passenger demand to concrete bus allocation recommendations.
    Pure domain logic — no database I/O, no external calls.
    """

    def compute_fleet_plan(self, route_data: dict, demand_data: dict) -> dict:
        return compute_fleet_plan(route_data, demand_data)

    # ──────────────────────────────────────────────────────────────────────
    # Single-route optimization (used by plan_trip)
    # ──────────────────────────────────────────────────────────────────────
    def optimize(
        self,
        route_predicted_passengers: int,
        bus_capacity: int         = 60,
        available_buses: int      = DEFAULT_FLEET_SIZE,
    ) -> dict:
        """
        Parameters
        ----------
        route_predicted_passengers : Total passengers expected on the entire route.
        bus_capacity         : Seated + standing capacity of a single bus.
        available_buses      : Total buses currently available for deployment.

        Returns
        -------
        {
            "required_buses"    : int,
            "available_buses"   : int,
            "fleet_gap"         : int,     # positive = shortage, negative = surplus
            "allocation_status" : str,     # "sufficient" | "shortage" | "surplus"
            "fleet_utilization" : int,     # 0-100 percent
            "unmet_demand"      : int,
        }
        """
        if bus_capacity <= 0:
            logger.error("bus_capacity must be > 0")
            bus_capacity = 60

        route_predicted_passengers = max(0, int(route_predicted_passengers))
        required_buses       = math.ceil(route_predicted_passengers / bus_capacity)
        fleet_gap            = required_buses - available_buses

        if fleet_gap > 0:
            allocation_status = "shortage"
        elif fleet_gap < 0:
            allocation_status = "surplus"
        else:
            allocation_status = "sufficient"

        deployed_buses = min(required_buses, available_buses)
        total_capacity = deployed_buses * bus_capacity

        # Utilization: demand served / total capacity deployed
        fleet_utilization = (
            min(100, int((route_predicted_passengers / total_capacity) * 100))
            if total_capacity > 0 else 0
        )

        # Unmet demand: passengers who cannot board given available fleet
        unmet_demand = max(0, route_predicted_passengers - available_buses * bus_capacity)

        result = {
            "required_buses"    : required_buses,
            "available_buses"   : available_buses,
            "fleet_gap"         : fleet_gap,
            "allocation_status" : allocation_status,
            "fleet_utilization" : fleet_utilization,
            "unmet_demand"      : unmet_demand,
        }

        logger.info(
            f"Fleet opt | demand={route_predicted_passengers} | "
            f"required={required_buses} | available={available_buses} | "
            f"status={allocation_status} | utilization={fleet_utilization}% | "
            f"unmet={unmet_demand}"
        )
        return result

    # ──────────────────────────────────────────────────────────────────────
    # Batch multi-route optimization (used by admin analytics)
    # ──────────────────────────────────────────────────────────────────────
    def batch_optimize(
        self,
        route_demands: Dict[str, int],
        bus_capacity: int          = 60,
        available_per_route: int   = DEFAULT_FLEET_SIZE_PER_ROUTE,
    ) -> Dict:
        """
        Compute per-route fleet allocation for all routes simultaneously.

        Parameters
        ----------
        route_demands       : {route_id: predicted_demand}
        bus_capacity        : Seats per bus.
        available_per_route : Buses available to each route.

        Returns
        -------
        {
            "per_route_breakdown": [
                {
                    "route_id"       : str,
                    "demand"         : int,
                    "required_buses" : int,
                    "fleet_gap"      : int,
                    "utilization"    : float,
                    "unmet_demand"   : int,
                    "status"         : str
                }
            ],
            "summary": {
                "total_demand"         : int,
                "total_required_buses" : int,
                "total_unmet_demand"   : int,
                "avg_utilization"      : float,
                "routes_in_shortage"   : int,
                "routes_in_surplus"    : int,
            }
        }
        """
        breakdown: List[Dict] = []
        total_demand         = 0
        total_required_buses = 0
        total_unmet          = 0
        utilization_sum      = 0.0
        shortage_count       = 0
        surplus_count        = 0

        for route_id, demand in route_demands.items():
            demand         = max(0, int(demand))
            req_buses      = math.ceil(demand / bus_capacity) if demand > 0 else 0
            avail          = available_per_route
            gap            = req_buses - avail
            deployed       = min(req_buses, avail)
            cap            = deployed * bus_capacity
            utilization    = round((demand / cap) * 100, 1) if cap > 0 else 0.0
            unmet          = max(0, demand - avail * bus_capacity)

            if gap > 0:
                status = "shortage"
                shortage_count += 1
            elif gap < 0:
                status = "surplus"
                surplus_count += 1
            else:
                status = "sufficient"

            breakdown.append({
                "route_id"       : route_id,
                "demand"         : demand,
                "required_buses" : req_buses,
                "fleet_gap"      : gap,
                "utilization"    : utilization,
                "unmet_demand"   : unmet,
                "status"         : status,
            })

            total_demand         += demand
            total_required_buses += req_buses
            total_unmet          += unmet
            utilization_sum      += utilization

        avg_util = round(utilization_sum / len(breakdown), 1) if breakdown else 0.0

        logger.info(
            f"Batch fleet opt | routes={len(breakdown)} | "
            f"total_demand={total_demand} | total_required={total_required_buses} | "
            f"unmet={total_unmet} | avg_util={avg_util}%"
        )

        return {
            "per_route_breakdown": breakdown,
            "summary": {
                "total_demand"         : total_demand,
                "total_required_buses" : total_required_buses,
                "total_unmet_demand"   : total_unmet,
                "avg_utilization"      : avg_util,
                "routes_in_shortage"   : shortage_count,
                "routes_in_surplus"    : surplus_count,
            },
        }

    # ──────────────────────────────────────────────────────────────────────
    # Frequency recommendation helpers
    # ──────────────────────────────────────────────────────────────────────
    @staticmethod
    def recommend_frequency(fleet_gap: int, current_headway_min: int = 10) -> dict:
        """
        Suggest headway adjustments based on fleet gap.

        Returns:
            { "recommended_headway_min": int, "action": str }
        """
        if fleet_gap > 2:
            new_headway = max(4, current_headway_min - 4)
            action = "Increase service frequency — critical shortage"
        elif fleet_gap > 0:
            new_headway = max(6, current_headway_min - 2)
            action = "Increase service frequency — minor shortage"
        elif fleet_gap < -3:
            new_headway = min(20, current_headway_min + 4)
            action = "Reduce service frequency — significant surplus"
        elif fleet_gap < 0:
            new_headway = min(15, current_headway_min + 2)
            action = "Reduce service frequency — minor surplus"
        else:
            new_headway = current_headway_min
            action = "Maintain current frequency"

        return {
            "recommended_headway_min": new_headway,
            "action": action,
        }

    # ──────────────────────────────────────────────────────────────────────
    # Dynamic recommendation text (Admin-focused)
    # ──────────────────────────────────────────────────────────────────────
    @staticmethod
    def generate_recommendation(
        fleet_gap: int,
        utilization: float,
        unmet_demand: int,
        predicted_demand: int,
    ) -> str:
        """
        Generate a human-readable recommendation based on live fleet metrics.
        Never hardcoded — all text derived from computed values.
        Admin-focused for fleet management.
        """
        if fleet_gap > 5:
            return (
                f"Critical shortage: Deploy {fleet_gap} additional buses immediately. "
                f"{unmet_demand} passengers cannot be served at current capacity."
            )
        elif fleet_gap > 0:
            return (
                f"Shortage detected: Allocate {fleet_gap} more bus(es) to meet demand. "
                f"Current utilization is {utilization:.0f}% with {unmet_demand} unserved passengers."
            )
        elif fleet_gap < -3:
            return (
                f"Significant surplus: Reduce fleet by {abs(fleet_gap)} buses to cut operational costs. "
                f"Fleet is at only {utilization:.0f}% utilization."
            )
        elif fleet_gap < 0:
            return (
                f"Minor surplus: Consider reassigning {abs(fleet_gap)} bus(es) to high-demand routes. "
                f"Utilization is {utilization:.0f}%."
            )
        else:
            return (
                f"Fleet balanced: {predicted_demand} passengers forecasted, "
                f"utilization at {utilization:.0f}%. No reallocation required."
            )

    # ──────────────────────────────────────────────────────────────────────
    # Passenger-focused recommendation text
    # ──────────────────────────────────────────────────────────────────────
    @staticmethod
    def generate_passenger_recommendation(
        eta_minutes: int,
        transfers: int,
        occupancy_percent: int,
        traffic_state: str,
        weather_condition: str,
        peak_status: str,
        has_alternatives: bool = False,
    ) -> str:
        """
        Generate passenger-friendly route recommendation.
        All text derived dynamically from computed values.
        """
        recommendations = []
        
        # Speed/efficiency
        if eta_minutes < 15:
            recommendations.append("This is a very quick route")
        elif eta_minutes < 25:
            recommendations.append("This route offers fast travel time")
        elif eta_minutes < 40:
            recommendations.append("This route offers reasonable travel time")
        else:
            recommendations.append("This route has a longer travel time")
        
        # Crowd level
        if occupancy_percent < 40:
            recommendations.append("with low expected crowd levels")
        elif occupancy_percent < 60:
            recommendations.append("with moderate crowd levels")
        elif occupancy_percent < 80:
            recommendations.append("with high crowd levels expected")
        else:
            recommendations.append("with very high crowd levels")
        
        # Transfers
        if transfers == 0:
            recommendations.append("and requires no transfers")
        elif transfers == 1:
            recommendations.append("with one transfer")
        else:
            recommendations.append(f"with {transfers} transfers")
        
        # Conditions
        if traffic_state == "Heavy":
            recommendations.append(". Expect delays due to heavy traffic")
        elif traffic_state == "High":
            recommendations.append(". Traffic may cause minor delays")
        
        if weather_condition in ["Rainy", "Storm"]:
            recommendations.append(f". Weather conditions may affect travel time")
        elif weather_condition == "Cloudy":
            recommendations.append(". Weather conditions are fair")
        
        # Peak status
        if peak_status == "morning_peak":
            recommendations.append(". Morning rush hour - consider departing earlier")
        elif peak_status == "evening_peak":
            recommendations.append(". Evening rush hour - expect higher demand")
        elif peak_status == "surge":
            recommendations.append(". High demand period - plan accordingly")
        
        # Alternatives
        if has_alternatives:
            recommendations.append(". Alternative routes may be available")
        
        return " ".join(recommendations) + "."


# Module-level singleton
fleet_optimization_service = FleetOptimizationService()
