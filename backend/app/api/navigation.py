"""
navigation.py — Internal routing endpoint for /api/navigation/plan

Previously called an external OpenTripPlanner (OTP) server at localhost:8080.
That server is not running, so all requests failed with "Internal OTP Mapping Error".

This version delegates to the same internal RAPTOR routing engine used by
POST /api/plan_trip (plan_trip_raptor + calculate_eta) and returns a
response shape that the frontend TripPlanner component expects.

NOTE: This previously called routing_service.resolve_route_dynamic (legacy
Dijkstra) directly and unconditionally, bypassing the USE_RAPTOR=true default
that /api/plan_trip uses. That made every chat-based trip request (via the
AI Assistant's _plan_trip -> plan_navigation) silently run on the slow,
known-bad engine — see routing_service._transfer_aware_dijkstra for its
documented scaling limits on this dataset's route density. Fixed to use
RAPTOR + the shared raptor_helpers conversion, matching api_routes.py.

NOTE (alternatives): generate_alternative_routes() calls the legacy
Dijkstra/NetworkX pathfinding stack (_compute_path_with_strategy) once per
strategy (up to 4x), with no internal timeout. On stop pairs with no
direct/shared route it falls through to an unbounded NetworkX search on
every strategy, which can take 10+ seconds combined and blow past the
AI Assistant's outer request budget — even though the primary route above
already resolved quickly via RAPTOR. It's now wrapped with a hard 3s
timeout and degrades to an empty alternatives list on timeout, since
alternates are a nice-to-have and should never block the primary answer.
"""

import concurrent.futures
import datetime
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database.connection import get_db, SessionLocal
from app.database.models import GTFSStop
from app.logger import app_logger
from app.cache import app_cache
from app.services.routing_service import generate_alternative_routes
from app.services.raptor_service import plan_trip_raptor
from app.services.raptor_helpers import convert_raptor_to_route_info
from app.services.eta_service import calculate_eta
from app.services.peak_hour_service import peak_hour_service
from app.services.schedule_engine import compute_route_frequency
from app.services.demand_prediction_service import demand_prediction_service
from app.services.fleet_optimization_service import (
    fleet_optimization_service, compute_demand_metrics,
    DEFAULT_FLEET_SIZE_PER_ROUTE,
)
from app.services.fare_service import fare_service
from app.services.vehicle_tracking_service import vehicle_tracking_service

router = APIRouter()

# Hard cap on time spent generating alternative routes. The primary route
# is already resolved via RAPTOR by the time we get here, so this only
# gates the "nice to have" alternates list.
ALTERNATIVES_TIMEOUT_SEC = 3.0


def _generate_alternatives_isolated(source_id: str, destination_id: str, traffic_state: str, weather_condition: str):
    """
    Runs generate_alternative_routes() on its own DB session, in a
    background thread. SQLAlchemy Session objects are not thread-safe,
    so this must NOT reuse the request-scoped `db` session that the main
    thread is still using concurrently (e.g. for leg/stop lookups right
    after this call is kicked off). Opens and closes its own session.
    """
    alt_db = SessionLocal()
    try:
        return generate_alternative_routes(
            alt_db, source_id, destination_id,
            bus_capacity=60, traffic=traffic_state, weather=weather_condition,
        )
    finally:
        alt_db.close()


@router.get("/api/navigation/plan")
def plan_navigation(source_id: str, destination_id: str, request: Request, db: Session = Depends(get_db)):
    """
    Plan a transit journey using the internal routing engine.
    Returns a response compatible with the frontend TripPlanner component.
    """
    # 1. Validate stops
    source_stop = db.query(GTFSStop).filter(GTFSStop.stop_id == source_id).first()
    dest_stop   = db.query(GTFSStop).filter(GTFSStop.stop_id == destination_id).first()

    if not source_stop:
        raise HTTPException(status_code=400, detail=f"Source stop ID '{source_id}' not found.")
    if not dest_stop:
        raise HTTPException(status_code=400, detail=f"Destination stop ID '{destination_id}' not found.")

    app_logger.info(f"Navigation plan: {source_stop.stop_name} → {dest_stop.stop_name}")

    current_hour = datetime.datetime.now().hour

    # 2. Route resolution using RAPTOR (matches /api/plan_trip's default engine —
    # do not fall back to resolve_route_dynamic; see routing_service._transfer_aware_dijkstra
    # for its documented scaling limits on this dataset's route density)
    try:
        now = datetime.datetime.now()
        start_time_sec = current_hour * 3600 + now.minute * 60 + now.second
        raptor_result = plan_trip_raptor(db, source_id, destination_id, start_time_sec, max_transfers=3)
        route_info = convert_raptor_to_route_info(raptor_result, db)
    except HTTPException as e:
        if e.status_code == 404:
            return {"success": False, "message": e.detail or "No route found between those stops."}
        raise
    except Exception as e:
        app_logger.exception("Navigation routing engine error")
        raise HTTPException(status_code=500, detail=f"Routing engine error: {str(e)}")

    # 3. Environmental context (weather + traffic)
    from app.database.models import WeatherRecord
    latest_weather = db.query(WeatherRecord).order_by(WeatherRecord.timestamp.desc()).first()
    if latest_weather:
        weather_condition = latest_weather.condition
        weather_full = f"{weather_condition}, {latest_weather.temperature}°C"
    else:
        weather_full = app_cache.get("weather") or "Clear, 28.0°C"
        weather_condition = weather_full.split(",")[0].strip()

    traffic_state = app_cache.get("traffic") or "Medium"

    # 3.5 Generate alternative routes (bounded)
    #
    # generate_alternative_routes() runs up to 4 full legacy pathfinding
    # searches (fastest / fewest transfers / shortest distance / least
    # walking), each via _compute_path_with_strategy. On stop pairs with
    # no direct/shared route, every one of those falls through to an
    # unbounded NetworkX fallback search — this is what produced the
    # 12+ second stalls (and eventual 15s AI Assistant timeout) on pairs
    # like Majestic -> Hebbal. The primary route has already been found
    # via RAPTOR above, so alternates are optional: cap the time spent
    # on them and degrade to an empty list rather than block the response.
    #
    # NOTE: future.result(timeout=...) does NOT cancel the underlying
    # thread — if generate_alternative_routes is still running past the
    # timeout, it keeps executing in the background until it finishes on
    # its own; the result is simply discarded. This is fine for occasional
    # slow pairs, but under sustained load on many slow pairs at once it
    # can pile up background threads doing wasted work against the DB
    # session. If that becomes a problem, generate_alternative_routes
    # itself should be made properly cancellable (e.g. short-circuit the
    # remaining strategies once "no shared route" is confirmed on the
    # first one) rather than relying solely on this timeout wrapper.
    #
    # IMPORTANT: do not wrap the executor in a `with` block. ThreadPoolExecutor's
    # __exit__ calls shutdown(wait=True), which blocks until the background
    # thread finishes NO MATTER WHAT — silently defeating future.result(timeout=...)
    # and making this whole block just as slow as the unbounded call it was
    # meant to replace. Manage the executor manually and shut it down with
    # wait=False so a timeout actually returns control immediately; the
    # abandoned thread just keeps running in the background until it
    # finishes on its own, and its result is discarded.
    alternative_routes = []
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    future = executor.submit(
        _generate_alternatives_isolated,
        source_id, destination_id, traffic_state, weather_condition,
    )
    try:
        alternative_routes = future.result(timeout=ALTERNATIVES_TIMEOUT_SEC)
    except concurrent.futures.TimeoutError:
        app_logger.warning(
            f"generate_alternative_routes exceeded {ALTERNATIVES_TIMEOUT_SEC}s budget "
            f"for {source_id}->{destination_id}; skipping alternates, "
            f"primary route already resolved via RAPTOR"
        )
    except Exception as e:
        app_logger.warning(f"Failed to generate alternative routes: {e}")
    finally:
        executor.shutdown(wait=False)

    # 4. ML Demand Prediction
    total_distance_km = route_info.get("total_distance_km") or 0.0
    bus_cap = 60

    peak_result = peak_hour_service.detect_peak_hour(current_hour)
    peak_status = peak_result["peak_status"]

    # Build complete feature set for CatBoost model
    current_dt = datetime.datetime.now()
    
    # Get route info for features
    route_id = route_info.get("route_id", "default")
    
    # Build complete feature dictionary (57 features)
    features = {
        "service_date": int(current_dt.strftime("%Y%m%d")),
        "route_id": route_id,
        "route_short_name": route_id[:10] if len(route_id) > 10 else route_id,
        "route_type": 3,
        "service_id": "default",
        "trip_id": f"trip_{route_id}_{current_hour}",
        "shape_id": f"shape_{route_id}",
        "direction_id": 0,
        "stop_id": source_id,
        "stop_name": source_stop.stop_name,
        "stop_sequence": 1,
        "stop_lat": float(source_stop.stop_lat) if source_stop.stop_lat else 0.0,
        "stop_lon": float(source_stop.stop_lon) if source_stop.stop_lon else 0.0,
        "terminal_stop_flag": 0,
        "major_interchange_flag": 1 if "Interchange" in source_stop.stop_name else 0,
        "area_type": "Mixed",
        "cumulative_distance": 0.0,
        "remaining_distance": total_distance_km,
        "number_of_stops": len(route_info.get("stops", [])),
        "remaining_stops": len(route_info.get("stops", [])),
        "route_length_km": total_distance_km,
        "scheduled_trip_duration": int((total_distance_km / 30.0) * 60),  # Estimate based on distance (30 km/h avg speed)
        "trip_start_time": current_hour * 60,
        "trip_end_time": (current_hour + 1) * 60,
        "hour": current_hour,
        "minute": current_dt.minute,
        "time_slot": "Morning" if current_hour < 12 else "Afternoon" if current_hour < 17 else "Evening",
        "day_of_week": current_dt.strftime("%A"),
        "weekday_weekend": "Weekday" if current_dt.weekday() < 5 else "Weekend",
        "month": current_dt.month,
        "holiday_flag": 0,
        "peak_hour_flag": 1 if peak_status != "normal" else 0,
        "weather_condition": weather_condition,
        "temperature": float(latest_weather.temperature) if latest_weather and latest_weather.temperature else 28.0,
        "rainfall_flag": 1 if weather_condition.lower() in ["rain", "rainy", "storm"] else 0,
        "congestion_index": 0.5 if traffic_state == "Medium" else 0.8 if traffic_state == "High" else 0.3,
        "traffic_level": traffic_state,
        "average_speed": 30.0,
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
        "vehicle_capacity": bus_cap,
        "boarding_count": 0,
        "alighting_count": 0,
        "onboard_passengers": 50,
        "occupancy_ratio": 0.5,
        "load_factor": 0.5,
        "demand_class": "Medium",
    }
    
    # Calculate journey split
    journey_stops = len(route_info.get("stops", []))
    total_route_stops = route_info.get("total_stops_on_route", max(journey_stops, 10))
    segment_ratio = max(0.1, min(1.0, journey_stops / total_route_stops))

    # Call ML prediction service
    app_logger.info(f"Calling demand prediction service for route {route_id}")
    prediction_result = demand_prediction_service.predict(features, segment_ratio=segment_ratio)
    
    route_demand = prediction_result.get("route_predicted_passengers", 0)
    journey_demand = prediction_result.get("journey_predicted_passengers", 0)
    demand_confidence = prediction_result.get("confidence", 0.97)
    model_source = prediction_result.get("model_source", "catboost")
    demand_class = prediction_result.get("demand_class", "Medium")
    
    app_logger.info(
        f"ML Prediction: route_demand={route_demand} journey_demand={journey_demand} passengers, "
        f"confidence={demand_confidence:.3f}, source={model_source}, class={demand_class}"
    )

    # Log warning if prediction failed
    if route_demand == 0 and journey_demand == 0:
        app_logger.warning(f"CatBoost prediction returned 0 for route {route_id}")
    
    # 5. ETA calculation with ML prediction
    eta_result    = calculate_eta(
        total_distance_km = total_distance_km,
        predicted_demand  = route_demand,
        bus_cap           = bus_cap,
        traffic_state     = traffic_state,
        weather_condition = weather_condition,
        peak_status       = peak_status,
    )
    eta_minutes = eta_result["eta_minutes"]

    # ── Unified Demand Metrics (single source of truth) ───────────────────
    # All fleet, occupancy, comfort, and recommendation fields must be read
    # from this object. Never recalculate them independently.
    # is_peak is derived from peak_status so navigation and plan_trip use
    # the same wait-time target and produce the same required_buses.
    dm = compute_demand_metrics(
        route_predicted_passengers=route_demand,
        journey_predicted_passengers=journey_demand,
        available_buses=DEFAULT_FLEET_SIZE_PER_ROUTE,
        bus_capacity=bus_cap,
        is_peak=bool(peak_status != "normal"),
    )

    # 6. Fleet Optimization (frequency/headway only — counts come from dm)
    fleet_result = fleet_optimization_service.optimize(
        route_predicted_passengers=route_demand,
        bus_capacity=bus_cap,
        available_buses=DEFAULT_FLEET_SIZE_PER_ROUTE,
    )
    optimization_status = dm["allocation_status"]
    fleet_utilization    = dm["ideal_occupancy_pct"]  # % of ideal capacity used

    # --- DIAGNOSTIC AUDIT LOGGING ---
    print("\n" + "="*50)
    print("ROUTE-SPECIFIC DIAGNOSTIC AUDIT")
    print(f"- source stop: {source_id}")
    print(f"- destination stop: {destination_id}")
    print(f"- selected route_id: {route_id}")
    print(f"- prediction source: {model_source}")
    # We don't have the raw prediction here directly, but we can reverse it from journey_demand for CatBoost
    raw_pred = journey_demand if model_source == "catboost" else route_demand
    print(f"- raw CatBoost prediction: {raw_pred}")
    print(f"- journey_predicted_passengers: {journey_demand}")
    print(f"- route_predicted_passengers: {route_demand}")
    print(f"- journey_stops: {journey_stops}")
    print(f"- total_route_stops: {total_route_stops}")
    print(f"- segment_ratio: {segment_ratio:.4f}")
    print(f"- required_buses: {dm['required_buses']}")
    print(f"- allocated_buses: {dm['allocated_buses']}")
    print(f"- available_buses: {dm['available_buses']}")
    print(f"- bus_capacity: 60")
    print(f"- occupancy_percentage: {dm['operational_occupancy_pct']}%")
    print(f"- crowd_level: {dm['crowd_level']}")
    print(f"- demand_level: {dm['demand_level']}")
    print("="*50 + "\n")
    # --------------------------------


    # Generate AI travel recommendation (ETA/weather context — separate from fleet rec)
    ai_recommendation = fleet_optimization_service.generate_passenger_recommendation(
        eta_minutes=eta_minutes,
        transfers=len(route_info.get("transfers", [])),
        occupancy_percent=int(dm["operational_occupancy_pct"]),
        traffic_state=traffic_state,
        weather_condition=weather_condition,
        peak_status=peak_status,
        has_alternatives=len(alternative_routes) > 0,
    )
    
    # 7. Service frequency with ML prediction
    route_freq = compute_route_frequency(
        route_id          = route_info["route_id"],
        passenger_demand  = route_demand,
        hour              = current_hour,
        traffic           = traffic_state,
        weather           = weather_full,
    )
    
    # Frequency recommendation (using dm["fleet_gap"])
    freq_rec = fleet_optimization_service.recommend_frequency(
        fleet_gap=dm["fleet_gap"],
        current_headway_min=route_freq.get("headway_minutes", 10),
    )
    optimized_frequency = freq_rec.get("recommended_headway_min")

    # 6. Build legs from route_legs or synthesise from stops
    raw_legs = route_info.get("route_legs") or []
    legs_out = []

    # Pre-build a stop_id -> stop_name lookup from DB for leg enrichment
    # Collect all stop IDs referenced in legs
    leg_stop_ids: set = set()
    for leg in raw_legs:
        if leg.get("from_stop"): leg_stop_ids.add(str(leg["from_stop"]))
        if leg.get("to_stop"):   leg_stop_ids.add(str(leg["to_stop"]))
    # Also always include source/dest
    leg_stop_ids.update([source_id, destination_id])

    stop_name_map: dict = {}
    if leg_stop_ids:
        db_stops = db.query(GTFSStop).filter(GTFSStop.stop_id.in_(list(leg_stop_ids))).all()
        for s in db_stops:
            stop_name_map[str(s.stop_id)] = s.stop_name

    if raw_legs:
        for leg in raw_legs:
            from_id = str(leg.get("from_stop", ""))
            to_id   = str(leg.get("to_stop",   ""))
            legs_out.append({
                "mode":           leg.get("mode", "BUS"),
                "route":          leg.get("route_id", route_info.get("route_id", "")),
                "route_name":     leg.get("route_name", ""),
                "from_stop":      from_id,
                "from_stop_name": stop_name_map.get(from_id) or from_id,
                "to_stop":        to_id,
                "to_stop_name":   stop_name_map.get(to_id) or to_id,
                "duration":       leg.get("duration_minutes", round(eta_minutes / max(len(raw_legs), 1), 1)),
                "geometry":       "",
            })
    else:
        # Synthesise a single leg from the full stop list
        stops_list = route_info.get("stops", [])
        from_id = str(stops_list[0]) if stops_list else source_id
        to_id   = str(stops_list[-1]) if stops_list else destination_id
        legs_out.append({
            "mode":           "BUS",
            "route":          route_info.get("route_id", ""),
            "route_name":     "",
            "from_stop":      from_id,
            "from_stop_name": stop_name_map.get(from_id) or source_stop.stop_name,
            "to_stop":        to_id,
            "to_stop_name":   stop_name_map.get(to_id) or dest_stop.stop_name,
            "duration":       eta_minutes,
            "geometry":       "",
        })

    # 7. Duration label
    duration_label = f"{int(eta_minutes)} min"

    # 8. Build polyline from route_path coordinates
    route_path = route_info.get("route_path", [])
    polyline_coords = [
        [pt["lat"], pt["lon"]]
        for pt in route_path
        if isinstance(pt, dict) and "lat" in pt and "lon" in pt
    ]

    response_payload = {
        "success":      True,
        "journey_id":   str(uuid.uuid4()),

        # Core trip info
        "source":       source_stop.stop_name,
        "destination":  dest_stop.stop_name,
        "route_id":     route_info.get("route_id", ""),
        "route_ids":    route_info.get("route_ids", []),

        # Timing
        "duration":     duration_label,
        "eta_minutes":  eta_minutes,
        "distance_km":  round(total_distance_km, 2),
        "fare":         fare_service.calculate_fare(route_info.get("route_id", ""), total_distance_km),
        "transfers":    len(route_info.get("transfers", [])),

        # Stops & path (used by RouteMap and progress bar)
        "stops":        route_info.get("stops", []),
        "route_path":   route_path,
        "legs":         legs_out,
        "polyline":     polyline_coords,

        # Live bus stub — occupancy from DemandMetrics (operational)
        "occupancy_percent":      dm["operational_occupancy_pct"],
        "ideal_occupancy_pct":    dm["ideal_occupancy_pct"],
        "crowd_level":            dm["crowd_level"],
        "comfort_level":          dm["comfort_level"],
    }
    
    # Try to find a live bus for this route using vehicle_tracking_service
    active_buses = vehicle_tracking_service.get_all_active_vehicles()
    route_buses = [b for b in active_buses if b["route_id"] == route_info.get("route_id", "")]
    
    if route_buses:
        live_bus = route_buses[0]
        response_payload["live_buses"] = [
            {
                "bus_id":            live_bus["bus_id"],
                "route_id":          live_bus["route_id"],
                "current_location":  route_info.get("stops", [source_stop.stop_name])[live_bus.get("current_stop_index", 0)],
                "status":            live_bus["status"],
                "occupancy_percent": live_bus["occupancy_percent"],
                "eta_minutes":       live_bus["eta_minutes"],
            }
        ]
        response_payload["bus_id"] = live_bus["bus_id"]
    else:
        # No vehicle assigned - return null instead of synthetic ID
        response_payload["bus_id"] = None
        response_payload["live_buses"] = []

    # Add remaining fields
    response_payload.update({
        # Service frequency
        "service_frequency": {
            "buses_per_hour":  route_freq["buses_per_hour"],
            "headway_minutes": route_freq["headway_minutes"],
            "frequency_tier":  route_freq["frequency_tier"],
            "label":           route_freq["label"],
            "is_peak":         route_freq["is_peak"],
        },

        # AI Transit Intelligence fields
        "predicted_demand":    journey_demand,
        "forecast_demand":     journey_demand,
        "demand_available":    journey_demand is not None and journey_demand > 0,
        "peak_status":         peak_status,
        "demand_confidence":   f"{demand_confidence:.2f}",

        # Fleet Optimization fields (from unified DemandMetrics)
        "current_fleet":       dm["available_buses"],
        "recommended_fleet":   dm["required_buses"],
        "additional_buses":    dm["additional_buses_needed"],
        "fleet_gap":           dm["fleet_gap"],
        "fleet_utilization":   fleet_utilization,
        "optimized_frequency": optimized_frequency,
        "optimization_status": dm["allocation_status"].capitalize(),
        "expected_waiting_time": route_freq.get("headway_minutes", 10),

        # Fleet Optimization fields (from unified DemandMetrics)
        "fleet_recommendation_text": dm["fleet_recommendation"],

        # AI Travel Recommendation (ETA/weather/comfort context — separate field)
        "ai_recommendation":         ai_recommendation,
        "recommendation_reason":     f"Based on {dm['journey_predicted_passengers']} journey predicted passengers and {dm['ideal_occupancy_pct']:.0f}% ideal occupancy",
        "transfer_details":          route_info.get("transfers", []),
        "recommendation_confidence": f"{demand_confidence:.2f}",

        # Alternative routes
        "alternative_routes": alternative_routes,

        # Context
        "context": {
            "weather":      weather_full,
            "traffic":      traffic_state,
            "demand_level": dm["demand_level"],
        },
        "weather": weather_full,
        "traffic": traffic_state,
    })

    return response_payload


@router.get("/api/navigation/alternatives")
def get_alternatives(source_id: str, destination_id: str, db: Session = Depends(get_db)):
    """
    Returns alternative routes. Currently returns an empty list as the internal
    engine produces a single best route; multi-path support can be added later.
    """
    return []


@router.get("/api/navigation/details")
def get_details(journey_id: str):
    return {"journey_id": journey_id, "status": "details placeholder"}