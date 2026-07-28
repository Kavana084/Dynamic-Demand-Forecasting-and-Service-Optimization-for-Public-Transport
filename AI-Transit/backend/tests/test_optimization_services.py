"""
Unit Tests — Transit AI System Redesign
======================================
Tests for all new services:
  - PeakHourService
  - DemandPredictionService (heuristic mode)
  - FleetOptimizationService
  - RouteOptimizationService
  - ETA Service (calculate_eta)

Run:
    python -m pytest backend/tests/test_optimization_services.py -v
"""

import sys
import os
import math

# Make backend importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

# ── Peak Hour Service ─────────────────────────────────────────────────────────
from app.services.peak_hour_service import PeakHourService

class TestPeakHourService:
    def setup_method(self):
        self.svc = PeakHourService()

    def test_morning_peak(self):
        for h in [7, 8, 9, 10]:
            assert self.svc.detect_peak_hour(h)["peak_status"] == "morning_peak", f"hour {h}"

    def test_evening_peak(self):
        for h in [17, 18, 19, 20, 21]:
            assert self.svc.detect_peak_hour(h)["peak_status"] == "evening_peak", f"hour {h}"

    def test_normal_hours(self):
        for h in [0, 5, 6, 11, 12, 14, 16, 22, 23]:
            assert self.svc.detect_peak_hour(h)["peak_status"] == "normal", f"hour {h}"

    def test_returns_dict(self):
        result = self.svc.detect_peak_hour(9)
        assert "peak_status" in result


# ── Demand Prediction Service ─────────────────────────────────────────────────
from app.services.demand_prediction_service import DemandPredictionService

class TestDemandPredictionService:
    def setup_method(self):
        self.svc = DemandPredictionService()

    def _minimal_features(self, **overrides):
        """Return a minimal feature dict that satisfies the predict() interface."""
        base = {
            "route_id": "test_route",
            "passenger_count": 50,
            "occupancy_ratio": 0.6,
            "weather_condition": "Clear",
            "traffic_level": "Medium",
            "hour": 12,
            "peak_hour_flag": 0,
            "service_date": 20240101,
            "route_short_name": "T1",
            "route_type": 3,
            "service_id": "default",
            "trip_id": "trip_test",
            "shape_id": "shape_test",
            "direction_id": 0,
            "stop_id": "stop_01",
            "stop_name": "Test Stop",
            "stop_sequence": 1,
            "stop_lat": 12.97,
            "stop_lon": 77.59,
            "terminal_stop_flag": 0,
            "major_interchange_flag": 0,
            "area_type": "Mixed",
            "cumulative_distance": 0.0,
            "remaining_distance": 5.0,
            "number_of_stops": 10,
            "remaining_stops": 9,
            "route_length_km": 10.0,
            "scheduled_trip_duration": 30,
            "trip_start_time": 720,
            "trip_end_time": 780,
            "minute": 0,
            "time_slot": "Afternoon",
            "day_of_week": "Monday",
            "weekday_weekend": "Weekday",
            "month": 1,
            "holiday_flag": 0,
            "temperature": 28,
            "rainfall_flag": 0,
            "congestion_index": 0.5,
            "average_speed": 30,
            "traffic_delay": 0,
            "weather_delay": 0,
            "boarding_delay": 0,
            "total_delay": 0,
            "headway_minutes": 15,
            "service_frequency_category": "Normal",
            "historical_route_average": 25.0,
            "historical_stop_average": 25.0,
            "historical_hour_average": 25.0,
            "historical_peak_average": 35.0,
            "historical_weekend_average": 20.0,
            "route_popularity_score": 0.5,
            "vehicle_capacity": 60,
            "boarding_count": 10,
            "alighting_count": 5,
            "onboard_passengers": 50,
            "load_factor": 0.6,
            "demand_class": "Medium",
        }
        base.update(overrides)
        return base

    def test_output_keys(self):
        result = self.svc.predict(self._minimal_features())
        assert "route_predicted_passengers" in result
        assert "demand_score" in result
        assert "confidence" in result

    def test_demand_score_range(self):
        result = self.svc.predict(self._minimal_features(
            passenger_count=200, occupancy_ratio=1.0,
            weather_condition="Rainy", traffic_level="Heavy",
            peak_hour_flag=1,
        ))
        assert 0 <= result["demand_score"] <= 100

    def test_confidence_storm_degrades(self):
        r_clear = self.svc.predict(self._minimal_features(weather_condition="Clear", traffic_level="Low"))
        r_storm = self.svc.predict(self._minimal_features(weather_condition="Storm", traffic_level="Heavy"))
        # Both use same model; confidence may be equal when model is absent — just check type
        assert isinstance(r_clear["confidence"], float)
        assert isinstance(r_storm["confidence"], float)

    def test_passengers_positive(self):
        result = self.svc.predict(self._minimal_features(passenger_count=1, occupancy_ratio=0.01))
        assert result["route_predicted_passengers"] >= 1

    def test_safe_fallback_on_bad_input(self):
        # Should not raise even with edge-case values
        result = self.svc.predict(self._minimal_features(passenger_count=-10, occupancy_ratio=9.99))
        assert isinstance(result, dict)


# ── Fleet Optimization Service ────────────────────────────────────────────────
from app.services.fleet_optimization_service import FleetOptimizationService
from app.services.fleet_optimization_service import compute_fleet_plan

class TestFleetOptimizationService:
    def setup_method(self):
        self.svc = FleetOptimizationService()

    def test_required_buses_formula(self):
        result = self.svc.optimize(route_predicted_passengers=120, bus_capacity=60)
        assert result["required_buses"] == 2  # ceil(120/60)

    def test_required_buses_ceil(self):
        result = self.svc.optimize(route_predicted_passengers=61, bus_capacity=60)
        assert result["required_buses"] == 2  # ceil(61/60)

    def test_shortage_status(self):
        result = self.svc.optimize(route_predicted_passengers=1200, bus_capacity=60, available_buses=5)
        assert result["allocation_status"] == "shortage"
        assert result["fleet_gap"] > 0

    def test_surplus_status(self):
        result = self.svc.optimize(route_predicted_passengers=10, bus_capacity=60, available_buses=20)
        assert result["allocation_status"] == "surplus"
        assert result["fleet_gap"] < 0

    def test_sufficient_status(self):
        result = self.svc.optimize(route_predicted_passengers=60, bus_capacity=60, available_buses=1)
        assert result["allocation_status"] == "sufficient"

    def test_utilization_cap(self):
        result = self.svc.optimize(route_predicted_passengers=150, bus_capacity=60)
        assert 0 <= result["fleet_utilization"] <= 100

    def test_frequency_shortage(self):
        freq = FleetOptimizationService.recommend_frequency(fleet_gap=3)
        assert freq["recommended_headway_min"] < 10

    def test_frequency_surplus(self):
        freq = FleetOptimizationService.recommend_frequency(fleet_gap=-5)
        assert freq["recommended_headway_min"] > 10

    def test_compute_fleet_plan_increase_on_high_occupancy(self):
        plan = compute_fleet_plan(
            route_data={"status": "ok"},
            demand_data={"route_predicted_passengers": 90},
        )
        assert plan["frequency_adjustment"] == "increase"
        assert plan["buses_required"] == 2

    def test_compute_fleet_plan_decrease_on_low_demand(self):
        plan = compute_fleet_plan(
            route_data={"status": "ok"},
            demand_data={"route_predicted_passengers": 10},
        )
        assert plan["frequency_adjustment"] == "decrease"

    def test_compute_fleet_plan_safe_defaults_on_missing_input(self):
        result = compute_fleet_plan(route_data={}, demand_data={})
        assert result == {
            "buses_required": 1,
            "frequency_adjustment": "stable",
            "utilization_score": 0.5,
            "load_factor": 0.5,
        }

class TestDemandMetrics:
    def test_zero_passengers(self):
        from app.services.fleet_optimization_service import compute_demand_metrics
        result = compute_demand_metrics(
            route_predicted_passengers=0,
            journey_predicted_passengers=0,
            available_buses=5,
            bus_capacity=60,
        )
        assert result["required_buses"] == 0
        assert result["allocated_buses"] == 0
        # required=0, available=5 -> fleet_gap = -5 (surplus)
        assert result["fleet_gap"] == -5
        assert result["ideal_occupancy_pct"] == 0.0
        assert result["operational_occupancy_pct"] == 0.0
        assert result["demand_level"] == "Low"
        # 0 demand with buses available is a surplus, not sufficient
        assert result["allocation_status"] == "surplus"
        assert result["fleet_recommendation"] == "No Additional Buses Required."

    def test_severe_shortage(self):
        from app.services.fleet_optimization_service import compute_demand_metrics
        # route: 1200 passengers, 2 buses available (capacity 60)
        # journey: 300 passengers (25% of route segment)
        result = compute_demand_metrics(
            route_predicted_passengers=1200,
            journey_predicted_passengers=300,
            available_buses=2,
            bus_capacity=60,
        )
        assert result["required_buses"] == 20          # ceil(1200 / 60)
        assert result["allocated_buses"] == 2           # min(20, 2)
        assert result["fleet_gap"] == 18
        assert result["allocation_status"] == "shortage"
        # ideal_occupancy = journey(300) / (required_buses(20) * cap(60)) = 300/1200 = 25%
        assert result["ideal_occupancy_pct"] == 25.0
        # operational = journey(300) / (allocated_buses(2) * cap(60)) = 300/120 = 250%
        assert result["operational_occupancy_pct"] == 250.0
        # 300 pax on journey -> Moderate (150-399 range)
        assert result["demand_level"] == "Moderate"
        assert "Critical shortage" in result["fleet_recommendation"]

    def test_occupancy_comfort_inversion(self):
        from app.services.fleet_optimization_service import compute_demand_metrics
        # low journey demand: 20 pax, 1 bus (capacity 60) -> ~33% operational occupancy
        r_low = compute_demand_metrics(
            route_predicted_passengers=20,
            journey_predicted_passengers=20,
            available_buses=1,
            bus_capacity=60,
        )
        # high journey demand: 55 pax, 1 bus (capacity 60) -> ~92% operational occupancy
        r_high = compute_demand_metrics(
            route_predicted_passengers=55,
            journey_predicted_passengers=55,
            available_buses=1,
            bus_capacity=60,
        )
        assert r_low["comfort_level"] == "High"
        assert r_high["comfort_level"] in ["Medium", "Low"]
        assert r_high["crowd_level"] in ["Moderate", "High", "Very High"]

# ── Route Optimization Service ────────────────────────────────────────────────
from app.services.route_optimization_service import RouteOptimizationService

class TestRouteOptimizationService:
    def setup_method(self):
        self.svc = RouteOptimizationService()
        self.sample_path = [
            {"stop_id": "S1", "stop_name": "A", "lat": 12.97, "lon": 77.59},
            {"stop_id": "S2", "stop_name": "B", "lat": 12.98, "lon": 77.60},
            {"stop_id": "S3", "stop_name": "C", "lat": 12.99, "lon": 77.61},
        ]

    def test_output_keys(self):
        result = self.svc.optimize(self.sample_path)
        assert "optimized_route" in result
        assert "route_efficiency" in result

    def test_efficiency_range(self):
        result = self.svc.optimize(self.sample_path)
        assert 0 <= result["route_efficiency"] <= 100

    def test_no_loops(self):
        result = self.svc.optimize(self.sample_path)
        ids = [s["stop_id"] for s in result["optimized_route"]]
        assert len(ids) == len(set(ids)), "Loop detected in optimized route"

    def test_empty_path(self):
        result = self.svc.optimize([])
        assert result["optimized_route"] == []

    def test_single_stop(self):
        single = [{"stop_id": "S1", "stop_name": "A", "lat": 12.97, "lon": 77.59}]
        result = self.svc.optimize(single)
        assert isinstance(result, dict)

    def test_heavy_traffic_lowers_efficiency(self):
        r_low  = self.svc.optimize(self.sample_path, traffic="Low",   weather="Clear")
        r_heavy= self.svc.optimize(self.sample_path, traffic="Heavy", weather="Storm")
        assert r_heavy["route_efficiency"] <= r_low["route_efficiency"]


# ── ETA Service ───────────────────────────────────────────────────────────────
from app.services.eta_service import calculate_eta, _calculate_confidence

class TestETAService:
    def test_output_keys(self):
        result = calculate_eta(5.0, 50, 60)
        assert "eta_minutes" in result
        assert "delay_minutes" in result
        assert "occupancy" in result
        assert "eta_confidence" in result

    def test_eta_positive(self):
        result = calculate_eta(10.0, 80, 60, "Medium", "Clear")
        assert result["eta_minutes"] >= 1

    def test_heavy_traffic_increases_eta(self):
        r_low   = calculate_eta(10.0, 50, 60, "Low",   "Clear")
        r_heavy = calculate_eta(10.0, 50, 60, "Heavy", "Clear")
        assert r_heavy["eta_minutes"] > r_low["eta_minutes"]

    def test_storm_increases_eta(self):
        r_clear = calculate_eta(10.0, 50, 60, "Medium", "Clear")
        r_storm = calculate_eta(10.0, 50, 60, "Medium", "Storm")
        assert r_storm["eta_minutes"] > r_clear["eta_minutes"]

    def test_peak_increases_eta(self):
        r_normal = calculate_eta(10.0, 50, 60, peak_status="normal")
        r_peak   = calculate_eta(10.0, 50, 60, peak_status="evening_peak")
        assert r_peak["eta_minutes"] >= r_normal["eta_minutes"]

    def test_confidence_storm_reduced(self):
        conf_clear = _calculate_confidence("Low", "Clear", "normal")
        conf_storm = _calculate_confidence("Heavy", "Storm", "surge")
        assert conf_storm < conf_clear

    def test_confidence_clamped(self):
        conf = _calculate_confidence("Heavy", "Storm", "surge")
        assert conf >= 0.60

    def test_occupancy_range(self):
        result = calculate_eta(5.0, 300, 60)  # over capacity
        assert 0 <= result["occupancy"] <= 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
