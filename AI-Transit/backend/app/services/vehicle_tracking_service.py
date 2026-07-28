import random
import datetime
import logging

from .peak_hour_service      import peak_hour_service
from .demand_prediction_service import demand_prediction_service
from .fleet_optimization_service import fleet_optimization_service
from .route_optimization_service import route_optimization_service
from .eta_service            import calculate_eta

logger = logging.getLogger(__name__)


class VehicleTrackingService:

    def __init__(self):
        self.active_vehicles: dict = {}

    # ------------------------------------------------------------------
    # Register
    # ------------------------------------------------------------------
    def register_trip(
        self,
        bus_id:            str,
        route_id:          str,
        route_path:        list,
        eta_minutes:       int,
        occupancy_percent: int,
        total_distance_km: float  = 5.0,
        bus_cap:           int    = 60,
        traffic_level:     str   = "Medium",
        weather_condition: str   = "Clear",
        transfer_count:    int   = 0,
    ):
        """Register a new trip into the active_vehicles store."""
        current_hour = datetime.datetime.now().hour
        peak_result  = peak_hour_service.detect_peak_hour(current_hour)

        self.active_vehicles[bus_id] = {
            # Identity
            "bus_id":            bus_id,
            "route_id":          route_id,
            "route_path":        route_path,
            "total_stops":       len(route_path),
            "current_stop_index": 0,
            # Distance & capacity context (needed for remaining-distance ETA)
            "total_distance_km": total_distance_km,
            "bus_cap":           bus_cap,
            "traffic_level":     traffic_level,
            "weather_condition": weather_condition,
            "transfer_count":    transfer_count,
            # Live state
            "occupancy_percent": occupancy_percent,
            "status":            "ACTIVE",
            # KPIs — seeded from initial eta
            "eta_minutes":       eta_minutes,
            "initial_eta":       eta_minutes,
            "delay_minutes":     0,
            "eta_confidence":    0.95,
            # Demand & fleet KPIs
            "predicted_demand":  occupancy_percent,  # best initial guess
            "demand_score":      50,
            "demand_confidence": 0.80,
            "required_buses":    1,
            "fleet_utilization": int((occupancy_percent / 100) * bus_cap),
            "fleet_gap":         0,
            "allocation_status": "sufficient",
            # Route KPIs
            "route_efficiency":  80,
            "peak_status":       peak_result["peak_status"],
            "optimization_score": 70,
        }
        logger.info(
            f"Trip registered | bus={bus_id} | route={route_id} | "
            f"dist={total_distance_km}km | peak={peak_result['peak_status']}"
        )

    # ------------------------------------------------------------------
    # State read
    # ------------------------------------------------------------------
    def get_vehicle_state(self, bus_id: str) -> dict | None:
        if bus_id not in self.active_vehicles:
            return None
        v = self.active_vehicles[bus_id]
        return {
            "bus_id":             v["bus_id"],
            "route_id":           v["route_id"],
            "current_stop_index": v["current_stop_index"],
            "occupancy_percent":  v["occupancy_percent"],
            "status":             v["status"],
            # ETA
            "eta_minutes":        v["eta_minutes"],
            "delay_minutes":      v["delay_minutes"],
            "eta_confidence":     v["eta_confidence"],
            # Demand
            "predicted_demand":   v["predicted_demand"],
            "demand_score":       v["demand_score"],
            "demand_confidence":  v["demand_confidence"],
            # Fleet
            "required_buses":     v["required_buses"],
            "fleet_utilization":  v["fleet_utilization"],
            "fleet_gap":          v["fleet_gap"],
            "allocation_status":  v["allocation_status"],
            # Route
            "route_efficiency":   v["route_efficiency"],
            # Intelligence
            "peak_status":        v["peak_status"],
            "optimization_score": v["optimization_score"],
        }

    # ------------------------------------------------------------------
    # Position update — core loop called by realtime_simulator every 5 s
    # ------------------------------------------------------------------
    def update_vehicle_position(self, bus_id: str) -> dict | None:
        if bus_id not in self.active_vehicles:
            return None

        v = self.active_vehicles[bus_id]

        if v["status"] == "COMPLETED":
            return self.get_vehicle_state(bus_id)

        total_stops = v["total_stops"]
        if total_stops <= 1:
            v["status"]      = "COMPLETED"
            v["eta_minutes"] = 0
            return self.get_vehicle_state(bus_id)

        # 1. Advance stop index
        if v["current_stop_index"] < total_stops - 1:
            v["current_stop_index"] += 1

        # 2. Simulate occupancy fluctuation
        occ_delta = random.randint(-3, 5)
        v["occupancy_percent"] = max(0, min(100, v["occupancy_percent"] + occ_delta))

        # 3. Peak-hour detection
        current_hour = datetime.datetime.now().hour
        peak_result  = peak_hour_service.detect_peak_hour(current_hour)
        peak_status  = peak_result["peak_status"]
        v["peak_status"] = peak_status

        # 4. Demand prediction
        demand_result = demand_prediction_service.predict_legacy(
            passenger_count   = int(v["occupancy_percent"] * v["bus_cap"] / 100),
            occupancy_percent = v["occupancy_percent"],
            weather           = v["weather_condition"],
            traffic           = v["traffic_level"],
            hour_of_day       = current_hour,
            day_of_week       = datetime.datetime.now().weekday(),
            peak_status       = peak_status,
        )
        v["predicted_demand"]  = demand_result["route_predicted_passengers"]
        v["demand_score"]      = demand_result["demand_score"]
        v["demand_confidence"] = demand_result["confidence"]

        # 5. Fleet optimization
        fleet_result = fleet_optimization_service.optimize(
            route_predicted_passengers = v["predicted_demand"],
            bus_capacity         = v["bus_cap"],
        )
        v["required_buses"]   = fleet_result["required_buses"]
        v["fleet_utilization"]= fleet_result["fleet_utilization"]
        v["fleet_gap"]        = fleet_result["fleet_gap"]
        v["allocation_status"]= fleet_result["allocation_status"]

        # 6. Route optimization
        remaining_path = v["route_path"][v["current_stop_index"]:]
        if len(remaining_path) >= 2:
            route_result = route_optimization_service.optimize(
                route_path = remaining_path,
                traffic    = v["traffic_level"],
                weather    = v["weather_condition"],
            )
            v["route_efficiency"] = route_result["route_efficiency"]

        # 7. ETA recalculation based on remaining distance
        progress_ratio     = v["current_stop_index"] / max(1, total_stops - 1)
        remaining_distance = max(0.1, v["total_distance_km"] * (1.0 - progress_ratio))

        eta_result = calculate_eta(
            total_distance_km  = remaining_distance,
            predicted_demand   = v["predicted_demand"],
            bus_cap            = v["bus_cap"],
            traffic_state      = v["traffic_level"],
            weather_condition  = v["weather_condition"],
            peak_status        = peak_status,
        )
        v["eta_minutes"]   = eta_result["eta_minutes"]
        v["delay_minutes"] = eta_result["delay_minutes"]
        v["eta_confidence"]= eta_result["eta_confidence"]

        # 8. Unified optimization score
        v["optimization_score"] = _compute_optimization_score(
            demand_score       = v["demand_score"],
            fleet_utilization  = v["fleet_utilization"],
            route_efficiency   = v["route_efficiency"],
            eta_confidence     = v["eta_confidence"],
        )

        # 9. Final stop check
        if v["current_stop_index"] >= total_stops - 1:
            v["status"]      = "COMPLETED"
            v["eta_minutes"] = 0

        return self.get_vehicle_state(bus_id)

    # ------------------------------------------------------------------
    # Batch helpers
    # ------------------------------------------------------------------
    def get_all_active_vehicles(self) -> list:
        return [
            self.get_vehicle_state(bus_id)
            for bus_id, v in self.active_vehicles.items()
            if v["status"] == "ACTIVE"
        ]


# ---------------------------------------------------------------------------
# Optimization Score Formula
# ---------------------------------------------------------------------------
def _compute_optimization_score(
    demand_score:      int,
    fleet_utilization: int,
    route_efficiency:  int,
    eta_confidence:    float,
) -> int:
    """
    optimization_score =
        demand_score      * 0.35
      + fleet_utilization * 0.30
      + route_efficiency  * 0.20
      + eta_confidence*100* 0.15

    Clamped to [0, 100].
    """
    score = (
        demand_score      * 0.35
        + fleet_utilization * 0.30
        + route_efficiency  * 0.20
        + eta_confidence * 100 * 0.15
    )
    return max(0, min(100, int(score)))


# Module-level singleton
vehicle_tracking_service = VehicleTrackingService()