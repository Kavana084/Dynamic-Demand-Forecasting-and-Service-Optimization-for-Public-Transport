from fastapi import APIRouter, HTTPException, Depends, Request
from typing import Dict, List, Any, Optional
import networkx as nx
from app.services.normalization_service import StopNormalizationService
import pandas as pd
import time
import datetime
import os
import sys
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if base_dir not in sys.path:
    sys.path.append(base_dir)

from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError
from app.database.connection import get_db, SessionLocal, check_db_connectivity
from app.database import crud

from . import service
from .optimization import optimize_fleet
from .validators import DemandPredictRequest, FleetOptimizeRequest
from .logger import log_execution_time, app_logger
from .cache import app_cache, save_to_disk, load_from_disk
from .services.schedule_engine import compute_route_frequency

# Constants
MAX_PASSENGERS = 300  # ceiling used to normalise demand_score 0-100

router = APIRouter()

from fastapi import Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os
from .services.auth_service import create_access_token, create_refresh_token, decode_access_token
from .services.user_service import authenticate_user, create_user
from .validators import LoginRequest, RegisterRequest, TokenResponse, AuthMessageResponse
from .dependencies import security, verify_admin, get_current_user_optional, require_passenger


def resolve_db_session(db):
    if isinstance(db, Session):
        return db, False

    temp_db = SessionLocal()
    return temp_db, True

@router.post("/api/auth/register", response_model=AuthMessageResponse)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    db, should_close = resolve_db_session(db)
    username = req.username.strip()
    password = req.password.strip()

    try:
        if not username:
            raise HTTPException(status_code=400, detail="Username is required")

        if not password:
            raise HTTPException(status_code=400, detail="Password is required")

        create_user(db, username=username, password=password, role="User")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        if should_close:
            db.close()

    return AuthMessageResponse(
        success=True,
        message="User registered successfully",
    )


@router.post("/api/auth/login", response_model=TokenResponse)
def login(req: LoginRequest, db: Session = Depends(get_db), authorization: str = Header(None)):
    db, should_close = resolve_db_session(db)
    normalized_username = req.username.strip().lower()
    auth_header_present = bool(authorization)

    app_logger.info(
        f"Login attempt | username={normalized_username} | authorization_header_present={auth_header_present}"
    )

    try:
        user = authenticate_user(db, req.username, req.password)
    finally:
        if should_close:
            db.close()

    if not user:
        app_logger.warning(
            f"Login failed | username={normalized_username} | authorization_header_present={auth_header_present}"
        )
        raise HTTPException(status_code=401, detail="Invalid credentials")

    app_logger.info(
        f"Login succeeded | username={user['username']} | role={user['role']} | authorization_header_present={auth_header_present}"
    )

    access_token = create_access_token(data={"sub": user["username"], "role": user["role"]})
    refresh_token = create_refresh_token(data={"sub": user["username"], "role": user["role"]})
    
    return TokenResponse(
        success=True,
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        role=user["role"]
    )

@router.post("/api/verify_admin")
def verify_admin_endpoint(user = Depends(verify_admin)):
    return {"ok": True, "user": user}

# Global state for cached dataset
dataset = None

def init_dataset(df: pd.DataFrame):
    global dataset
    dataset = df

@router.post("/api/predict_demand")
@log_execution_time("predict_demand")
def predict_demand(req: DemandPredictRequest, request: Request, db: Session = Depends(get_db)):
    svc = getattr(request.app.state, "prediction_service", None)
    if svc is None or svc.model is None:
        raise HTTPException(status_code=503, detail=f"Model not loaded. svc type: {type(svc)}, model type: {type(getattr(svc, 'model', None))}")
        
    app_logger.info(f"Prediction request | route={req.route_id} | hour={req.hour}")
    
    # Check cache
    cache_key = f"demand_{req.route_id}_{req.hour}_{req.weather}"
    cached_val = app_cache.get(cache_key)
    if cached_val is not None:
        app_logger.info(f"Cache hit | route={req.route_id} | hour={req.hour}")
        return {"route_id": req.route_id, "predicted_demand": cached_val, "cached": True}
        
    demand = svc.predict_demand(
        route_id=req.route_id, 
        hour=req.hour, 
        weather_condition=req.weather, 
        traffic=req.traffic
    )
    
    # AUDIT FIX 2A — Restore DB Inserts for Predictions
    try:
        now = datetime.datetime.utcnow()
        target_timestamp = now.replace(hour=req.hour, minute=0, second=0, microsecond=0)
        if req.hour < now.hour:
            target_timestamp += datetime.timedelta(days=1)
            
        crud.create_prediction(
            db=db,
            route_id=req.route_id,
            predicted_passengers=demand,
            confidence_score=None,
            model_version="catboost",
            target_timestamp=target_timestamp
        )
    except Exception as e:
        app_logger.error(f"Failed to insert prediction to DB: {str(e)}")
        
    # Store in cache for 1 hour
    app_cache.set(cache_key, demand, ttl_seconds=3600)
    
    return {"route_id": req.route_id, "predicted_demand": demand, "cached": False}

@router.post("/api/optimize_fleet")
@log_execution_time("optimize_fleet")
def optimize_fleet_api(req: FleetOptimizeRequest, request: Request, db: Session = Depends(get_db)):
    dataset = getattr(request.app.state, "dataset", None)
    if dataset is None:
        raise HTTPException(status_code=503, detail="Dataset not loaded")
        
    app_logger.info(f"Optimizing fleet with bus_capacity: {req.bus_capacity}")
    
    # Check cache
    cache_key = f"optimize_{req.bus_capacity}_{req.max_buses_per_route}_{req.cost_per_bus}_{req.penalty_unmet_demand}"
    cached_val = app_cache.get(cache_key)
    if cached_val is not None:
        app_logger.info("Cache hit for fleet optimization")
        return cached_val
        
    # Extract the prediction service
    svc = getattr(request.app.state, "prediction_service", None)
    if svc is None or svc.model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
        
    # Get real-time context from APScheduler cache
    weather = app_cache.get('weather') or 'clear'
    traffic = app_cache.get('traffic') or 'medium'
    current_hour = datetime.datetime.now().hour
        
    # Dynamically generate demand using ML model for each route
    unique_routes = dataset['route_id'].unique()
    route_demands = {}
    
    app_logger.info(f"Generating dynamic demand for {len(unique_routes)} routes. Weather: {weather}, Traffic: {traffic}")
    
    for r_id in unique_routes:
        route_demands[str(r_id)] = svc.predict_demand(
            route_id=str(r_id), 
            hour=current_hour, 
            weather_condition=weather, 
            traffic=traffic
        )
    
    # Run optimization
    try:
        result = optimize_fleet(
            route_demands=route_demands,
            bus_capacity=req.bus_capacity,
            max_buses_per_route=req.max_buses_per_route,
            cost_per_bus=req.cost_per_bus,
            penalty_unmet_demand=req.penalty_unmet_demand,
            alpha=req.alpha,
            beta=req.beta,
            gamma=req.gamma,
            delta=req.delta
        )
        if result.get("status") == "error":
            raise Exception(result.get("error_details"))
            
        # AUDIT FIX 2B — Restore DB Inserts for Optimizations
        try:
            for allocation in result.get("route_allocation", []):
                crud.create_optimization_result(
                    db=db,
                    route_id=allocation["route_id"],
                    allocated_buses=allocation["buses_assigned"],
                    utilization=allocation["utilization_percent"],
                    objective_score=allocation.get("objective_score")
                )
        except Exception as e:
            app_logger.error(f"Failed to insert optimization results to DB: {str(e)}")
            
        result["cached"] = False
        app_cache.set(cache_key, result, ttl_seconds=3600)
        app_cache.set("latest_optimization", result, ttl_seconds=3600) # Save for dashboard
        
        # Save to disk
        result["timestamp"] = datetime.datetime.now().isoformat()
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        output_file = os.path.join(base_dir, 'outputs', 'latest_optimization.json')
        save_to_disk(result, output_file)
        
        app_logger.info(f"Optimization completed | routes={len(route_demands)} | status={result.get('status')}")
        return result
        
    except Exception as e:
        app_logger.error(f"MILP Solver Failed: {str(e)}")
        # Fallback to last valid cached solution
        last_valid = app_cache.get("latest_optimization")
        if last_valid:
            last_valid["fallback_used"] = True
            last_valid["cached"] = True
            return last_valid
        else:
            raise HTTPException(status_code=500, detail="MILP solver failed and no fallback cache is available.")

@router.get("/api/dashboard")
def get_dashboard(db: Session = Depends(get_db)):
    # 1. Fetch DB Aggregations
    summary = crud.get_dashboard_summary(db)
    hourly_demand = crud.get_hourly_demand_trend(db)
    daily_trend = crud.get_daily_volume_trend(db)
    route_demand = crud.get_route_popularity(db)
    
    # 2. Fetch Latest Optimization from Database for Fleet Metrics
    # Query the most recent optimization results and sum allocated buses
    from app.database.models import OptimizationResult
    from datetime import datetime, timedelta
    
    # Get optimization results from the last 24 hours
    twenty_four_hours_ago = datetime.utcnow() - timedelta(hours=24)
    recent_opts = db.query(OptimizationResult).filter(
        OptimizationResult.timestamp >= twenty_four_hours_ago
    ).order_by(OptimizationResult.timestamp.desc()).all()
    
    # Calculate total allocated buses from ALL results in last 24 hours (accumulates on each Check Demand)
    if recent_opts:
        total_allocated_buses = sum(int(o.allocated_buses or 0) for o in recent_opts)
        avg_utilization = sum(float(o.utilization or 0) for o in recent_opts) / len(recent_opts) if recent_opts else 0
    else:
        total_allocated_buses = 0
        avg_utilization = 0
    
    fleet_summary = {
        "available": 1000,
        "optimizedAllocation": total_allocated_buses,
        "utilization": avg_utilization,
        "allocations": [{"route": o.route_id, "buses": o.allocated_buses} for o in recent_opts[:10]] if recent_opts else []
    }
    
    # 3. Deterministic Decision Support Engine (Replaces Mocked DRL)
    dse_recommendation = {
        "action": "Maintain current allocations",
        "expectedReward": "+0.0% Efficiency",
        "confidence": "100%",
        "priorityRoutes": []
    }
    
    # Calculate total unmet demand from database results
    total_unmet_demand = sum(int(o.unserved_demand or 0) for o in recent_opts) if recent_opts else 0
    
    if total_unmet_demand > 0:
        # Find route with highest unmet demand
        if recent_opts:
            worst_route = max(recent_opts, key=lambda x: int(x.unserved_demand or 0))
            if worst_route.unserved_demand and worst_route.unserved_demand > 0:
                dse_recommendation = {
                    "action": f"Increase buses on {worst_route.route_id}",
                    "expectedReward": "Minimize unmet demand",
                    "confidence": "High",
                    "priorityRoutes": [worst_route.route_id]
                }
    elif fleet_summary["utilization"] < 60 and fleet_summary["optimizedAllocation"] > 0:
        # Find most underutilized route
        if recent_opts:
            lowest_util = min(recent_opts, key=lambda x: float(x.utilization or 100))
            if lowest_util.utilization and lowest_util.utilization < 50:
                dse_recommendation = {
                    "action": f"Reduce buses on {lowest_util.route_id} (Underutilized)",
                    "expectedReward": "Save operational costs",
                    "confidence": "High",
                    "priorityRoutes": [lowest_util.route_id]
                }
                
    # 4. Construct Payload
    return {
        "kpis": summary,
        "hourlyDemand": hourly_demand,
        "dailyTrend": daily_trend,
        "routeDemand": route_demand,
        "fleetSummary": fleet_summary,
        "drlRecommendation": dse_recommendation,
        "systemHealth": "Unavailable",
        "modelMetrics": "Unavailable",
        "mapNodes": []
    }

@router.get("/api/dashboard/summary")
@log_execution_time("dashboard_summary")
def get_dashboard_summary(request: Request):
    cached_val = app_cache.get("latest_optimization")
    if not cached_val:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        output_file = os.path.join(base_dir, 'outputs', 'latest_optimization.json')
        cached_val = load_from_disk(output_file)
        if cached_val:
            app_logger.info("Dashboard summary | source=disk")
            app_cache.set("latest_optimization", cached_val, ttl_seconds=3600)
        else:
            raise HTTPException(status_code=503, detail="No optimization data available yet. Please run /api/optimize_fleet first.")
    else:
        app_logger.info("Dashboard summary | source=cache")
        
    summary = cached_val.get("summary", {})
    return {
        "system_status": "Online (ML-Driven)",
        "total_passengers_served": summary.get("total_passengers_served", 0),
        "total_buses_used": summary.get("total_buses_used", 0),
        "efficiency_percent": summary.get("overall_efficiency_percent", 0),
        "total_unmet_demand": summary.get("total_unmet_demand", 0)
    }

@router.get("/api/dashboard/heatmap")
@log_execution_time("dashboard_heatmap")
def get_dashboard_heatmap(request: Request):
    cache_key = "dashboard_heatmap"
    cached_val = app_cache.get(cache_key)
    if cached_val:
        return cached_val
        
    svc = getattr(request.app.state, "prediction_service", None)
    dataset = getattr(request.app.state, "dataset", None)
    if svc is None or svc.model is None or dataset is None:
        raise HTTPException(status_code=503, detail="Model or dataset not loaded")
        
    weather = app_cache.get('weather') or 'clear'
    traffic = app_cache.get('traffic') or 'medium'
    
    unique_routes = dataset['route_id'].unique().tolist()
    # Limit to 20 routes for performance if dataset is huge
    if len(unique_routes) > 20:
        unique_routes = unique_routes[:20]
        
    peak_hours = [8, 9, 10, 17, 18, 19]
    matrix = []
    
    for h in peak_hours:
        row = []
        for r_id in unique_routes:
            demand = svc.predict_demand(str(r_id), h, weather, traffic)
            row.append(demand)
        matrix.append(row)
        
    result = {
        "hours": peak_hours,
        "routes": unique_routes,
        "demand_matrix": matrix
    }
    app_cache.set(cache_key, result, ttl_seconds=3600)
    return result

@router.get("/api/dashboard/utilization")
@log_execution_time("dashboard_utilization")
def get_dashboard_utilization(request: Request):
    cached_val = app_cache.get("latest_optimization")
    if not cached_val:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        output_file = os.path.join(base_dir, 'outputs', 'latest_optimization.json')
        cached_val = load_from_disk(output_file)
        if cached_val:
            app_logger.info("Dashboard utilization | source=disk")
            app_cache.set("latest_optimization", cached_val, ttl_seconds=3600)
        else:
            raise HTTPException(status_code=503, detail="No optimization data available yet. Please run /api/optimize_fleet first.")
    else:
        app_logger.info("Dashboard utilization | source=cache")
        
    routes_status = []
    for route in cached_val.get("route_allocation", []):
        util = route.get("utilization_percent", 0)
        if util < 70:
            status = "underutilized"
        elif util <= 85:
            status = "optimal"
        else:
            status = "high efficiency"
            
        routes_status.append({
            "route_id": route["route_id"],
            "utilization_percent": util,
            "status": status,
            "buses_assigned": route["buses_assigned"]
        })
        
    return {"route_utilization": routes_status}

@router.get("/api/dashboard/forecast_trend/{route_id}")
@log_execution_time("dashboard_forecast_trend")
def get_dashboard_forecast_trend(route_id: str, request: Request):
    svc = getattr(request.app.state, "prediction_service", None)
    if svc is None or svc.model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
        
    weather = app_cache.get('weather') or 'clear'
    traffic = app_cache.get('traffic') or 'medium'
    
    trend = []
    for h in range(24):
        demand = svc.predict_demand(route_id, h, weather, traffic)
        trend.append({"hour": h, "predicted_demand": demand})
        
    return {
        "route_id": route_id,
        "trend": trend
    }

@router.get("/api/routes")
@log_execution_time("get_routes")
def get_routes(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    # Fetch GTFS Routes dynamically
    routes = db.query(Route).filter(Route.route_long_name.isnot(None)).offset(skip).limit(limit).all()
    if routes:
        return [{"id": r.route_id, "route_id": r.route_short_name or r.route_id, "name": r.route_long_name, "description": "GTFS Route"} for r in routes]
    
    routes = crud.get_routes(db, skip=skip, limit=limit)
    if not routes and dataset is not None:
        unique_route_ids = dataset['route_id'].unique().tolist()
        return [{"id": i, "route_id": str(r), "name": f"Route {r}", "description": "Auto-discovered route"} for i, r in enumerate(unique_route_ids[:limit])]
    return routes

@router.get("/api/stops")
@log_execution_time("get_stops")
def get_stops(db: Session = Depends(get_db), request: Request = None):
    if request and hasattr(request.app.state, "db_connected") and not request.app.state.db_connected:
        raise HTTPException(status_code=503, detail="Database is offline. Service unavailable in degraded mode.")
    try:
        stops = db.query(GTFSStop).order_by(GTFSStop.stop_name).all()
        seen = set()
        deduped_stops = []
        for s in stops:
            if s.stop_name and s.stop_name not in seen:
                seen.add(s.stop_name)
                deduped_stops.append({"stop_id": s.stop_id, "stop_name": s.stop_name, "lat": s.stop_lat, "lon": s.stop_lon})
        return deduped_stops
    except Exception as e:
        app_logger.error(f"Failed to query stops: {e}")
        raise HTTPException(status_code=503, detail="Database connection failed. Service unavailable.")

@router.get("/api/stops/{stop_id}/arrivals")
@log_execution_time("get_stop_arrivals")
def get_stop_arrivals(stop_id: str, request: Request, db: Session = Depends(get_db)):
    """
    Get live arrival times for a specific stop.
    Returns estimated arrival times based on GTFS scheduled stop times.
    """
    from app.database.models import Route, GTFSStopTime, GTFSTrip, GTFSStop
    from datetime import datetime, timedelta
    
    # Validate stop exists
    stop = db.query(GTFSStop).filter(GTFSStop.stop_id == stop_id).first()
    if not stop:
        raise HTTPException(status_code=404, detail=f"Stop {stop_id} not found")
    
    now = datetime.now()
    current_time_str = now.strftime("%H:%M:%S")
    # For night times, GTFS arrival_time can be >= 24:00:00, but we'll use simple string comparison
    
    # Get upcoming stop times for this stop, joined with trip to get route
    upcoming = db.query(
        GTFSStopTime.arrival_time, 
        GTFSTrip.route_id
    ).join(
        GTFSTrip, GTFSStopTime.trip_id == GTFSTrip.trip_id
    ).filter(
        GTFSStopTime.stop_id == stop_id,
        GTFSStopTime.arrival_time >= current_time_str
    ).order_by(
        GTFSStopTime.arrival_time
    ).all()
    
    if not upcoming:
        return []
    
    arrivals = []
    seen_routes = set()
    
    for arrival_time_str, route_id in upcoming:
        if route_id in seen_routes:
            continue
            
        seen_routes.add(route_id)
        if len(seen_routes) > 5:  # Limit to 5 upcoming routes
            break
            
        # Parse arrival time
        try:
            h, m, s = map(int, arrival_time_str.split(':'))
            # Handle GTFS times like 24:xx or 25:xx
            days = h // 24
            h = h % 24
            
            arrival_dt = datetime(now.year, now.month, now.day, h, m, s)
            if days > 0:
                arrival_dt += timedelta(days=days)
            elif arrival_dt < now:
                # If we passed midnight but are querying early morning, next day
                arrival_dt += timedelta(days=1)
                
            eta_minutes = int((arrival_dt - now).total_seconds() / 60)
        except ValueError:
            eta_minutes = 0
            
        # Get route info
        route = db.query(Route).filter(Route.route_id == route_id).first()
        
        # Get occupancy from prediction service if available
        svc = getattr(request.app.state, "prediction_service", None)
        weather = app_cache.get('weather') or 'clear'
        traffic = app_cache.get('traffic') or 'medium'
        
        occupancy = 50  # Default
        if svc and svc.model:
            try:
                demand = svc.predict_demand(route_id, now.hour, weather, traffic)
                occupancy = min(100, max(0, int((demand / 60) * 100)))
            except:
                pass
        
        arrivals.append({
            "route_id": route_id,
            "route_name": route.route_long_name if route else f"Route {route_id}",
            "eta_minutes": max(0, eta_minutes),
            "occupancy_percent": occupancy,
            "delay_minutes": 0  # GTFS schedule has no delay by definition, would need real-time data
        })
    
    # Sort by ETA
    arrivals.sort(key=lambda x: x["eta_minutes"])
    
    return arrivals

@router.get("/api/routes/nearby")
@log_execution_time("get_nearby_routes")
def get_nearby_routes(lat: float, lon: float, radius: float = 5.0, db: Session = Depends(get_db)):
    """
    Get routes near a specific location.
    Uses Haversine distance to find routes within radius km.
    """
    from app.database.models import Route, GTFSStop
    import math
    
    # Get all stops within radius
    stops = db.query(GTFSStop).all()
    nearby_stops = []
    
    for stop in stops:
        if stop.stop_lat and stop.stop_lon:
            # Haversine distance
            R = 6371  # Earth's radius in km
            dlat = math.radians(stop.stop_lat - lat)
            dlon = math.radians(stop.stop_lon - lon)
            a = (math.sin(dlat/2)**2 + 
                 math.cos(math.radians(lat)) * math.cos(math.radians(stop.stop_lat)) * 
                 math.sin(dlon/2)**2)
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
            distance = R * c
            
            if distance <= radius:
                nearby_stops.append((stop, distance))
    
    # Sort by distance
    nearby_stops.sort(key=lambda x: x[1])
    
    # Get unique routes from nearby stops
    route_ids = set()
    for stop, _ in nearby_stops[:20]:  # Limit to 20 closest stops
        from app.database.models import StopTime
        stop_times = db.query(StopTime).filter(StopTime.stop_id == stop.stop_id).limit(5).all()
        for st in stop_times:
            if hasattr(st, 'trip') and st.trip:
                route_ids.add(st.trip.route_id)
    
    # Get route details
    routes = []
    for route_id in list(route_ids)[:10]:  # Limit to 10 routes
        route = db.query(Route).filter(Route.route_id == route_id).first()
        if route:
            # Calculate average distance to this route
            route_distance = min([d for s, d in nearby_stops if any(
                hasattr(st, 'trip') and st.trip and st.trip.route_id == route_id
                for st in db.query(StopTime).filter(StopTime.stop_id == s.stop_id).limit(1).all()
            )], default=0)
            
            routes.append({
                "route_id": route_id,
                "route_name": route.route_long_name or f"Route {route_id}",
                "distance_km": round(route_distance),
                "status": "On time"
            })
    
    # Sort by distance
    routes.sort(key=lambda x: x["distance_km"])
    
    return routes

@router.get("/api/graph_diagnostics")
@log_execution_time("graph_diagnostics")
def graph_diagnostics(db: Session = Depends(get_db)):
    """
    Returns a full diagnostic report of the transit graph.
    Includes: node/edge counts, self-loops, disconnected nodes,
    strongly connected components (cycles), and duplicate stop names.
    """
    from .services.routing_service import get_graph_diagnostics
    return get_graph_diagnostics(db)

@router.get("/api/graph_statistics")
@log_execution_time("graph_statistics")
def graph_statistics(db: Session = Depends(get_db)):
    """
    Returns performance-profiling statistics about the transit graph.
    Includes: parallelism factor, unique stop-pair count, unique route triples,
    max/mean parallel edges, and top-10 routes by edge count.
    Use this to understand why N stops produce M >> N edges.
    """
    from .services.routing_service import get_graph_statistics
    return get_graph_statistics(db)

@router.get("/api/test_model_loading_script")
def test_model_loading_script():
    import sys
    import os
    import traceback
    from io import StringIO
    old_stdout = sys.stdout
    sys.stdout = mystdout = StringIO()
    try:
        import importlib
        import scripts.test_model_loading
        importlib.reload(scripts.test_model_loading)
        scripts.test_model_loading.test_model_loading()
    except Exception as e:
        traceback.print_exc()
    sys.stdout = old_stdout
    return {"output": mystdout.getvalue()}

@router.post("/api/graph_cache_reset")
def graph_cache_reset(user=Depends(verify_admin)):
    """Admin-only: invalidate the in-memory transit graph cache so it rebuilds on next route request."""
    from .services.routing_service import invalidate_transit_graph_cache
    invalidate_transit_graph_cache()
    return {"ok": True, "message": "Transit graph cache cleared. It will rebuild on the next /api/plan_trip call."}


@router.get("/api/predictions")
@log_execution_time("get_predictions")
def get_predictions(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    predictions = crud.get_predictions(db, skip=skip, limit=limit)
    return predictions

@router.get("/api/health")
def get_health(request: Request):
    app_logger.info("Health check requested")
    svc = getattr(request.app.state, "prediction_service", None)
    model_loaded = svc is not None and svc.model is not None
    
    # Check db
    db_connected = check_db_connectivity()
    request.app.state.db_connected = db_connected
        
    # Check cache and disk persistence
    cache_available = app_cache is not None
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    output_file = os.path.join(base_dir, 'outputs', 'latest_optimization.json')
    disk_persistence_available = os.path.exists(output_file)
    
    # Check other services
    weather_data = app_cache.get('weather')
    weather_status = "healthy" if weather_data else "unavailable"
    
    from app.task_scheduler import scheduler
    scheduler_status = "running" if scheduler.running else "stopped"
    
    from app.services.routing_service import transit_graph_cache
    routing_status = "warmed" if transit_graph_cache is not None else "cold"
    
    return {
      "status": "degraded" if not db_connected else "healthy",
      "model_loaded": model_loaded,
      "optimizer_ready": True,
      "database_connected": db_connected,
      "cache_available": cache_available,
      "disk_persistence_available": disk_persistence_available,
      "weather_service": weather_status,
      "scheduler": scheduler_status,
      "routing_service": routing_status
    }

@router.get("/api/admin/pipeline/validation")
def get_pipeline_validation(db: Session = Depends(get_db), admin=Depends(verify_admin)):
    from app.database.models import JourneyHistory, DemandHistory, ForecastHistory, OptimizationResult, PipelineRun

    journey_count = db.query(JourneyHistory).count()
    demand_count = db.query(DemandHistory).count()
    prediction_count = db.query(ForecastHistory).count()
    optimization_count = db.query(OptimizationResult).count()

    def get_status(c):
        return "healthy" if c > 0 else "empty"

    journey_status = get_status(journey_count)
    demand_status = get_status(demand_count)
    prediction_status = get_status(prediction_count)
    optimization_status = get_status(optimization_count)

    statuses = [journey_status, demand_status, prediction_status, optimization_status]
    if "unavailable" in statuses:
        overall = "unavailable"
    elif "degraded" in statuses:
        overall = "degraded"
    elif all(s == "healthy" for s in statuses):
        overall = "healthy"
    elif all(s == "empty" for s in statuses):
        overall = "empty"
    else:
        overall = "partial"

    def get_last_run(job_type):
        run = db.query(PipelineRun).filter(PipelineRun.job_type == job_type).order_by(PipelineRun.id.desc()).first()
        if run and run.completed_at:
            return run.completed_at.isoformat()
        elif run and run.started_at:
            return run.started_at.isoformat()
        return None

    return {
        "journey_history": {
            "count": journey_count,
            "status": journey_status
        },
        "demand_history": {
            "count": demand_count,
            "status": demand_status
        },
        "prediction_records": {
            "count": prediction_count,
            "status": prediction_status
        },
        "optimization_results": {
            "count": optimization_count,
            "status": optimization_status
        },
        "aggregation_last_run": get_last_run("aggregation"),
        "forecasting_last_run": get_last_run("forecasting"),
        "optimization_last_run": get_last_run("optimization"),
        "overall_status": overall
    }

@router.get("/api/admin/diagnostic")
def db_diagnostic(db: Session = Depends(get_db)):
    import traceback
    from app.database.models import JourneyHistory, DemandHistory, ForecastHistory, OptimizationResult, PipelineRun
    results = {}
    for model in [JourneyHistory, DemandHistory, ForecastHistory, OptimizationResult, PipelineRun]:
        try:
            count = db.query(model).count()
            results[model.__name__] = f"OK: {count}"
        except Exception as e:
            results[model.__name__] = f"ERROR: {str(e)}"
            db.rollback()
            
    # Also check if create_all works
    from app.database.connection import engine, Base
    try:
        Base.metadata.create_all(bind=engine)
        results["create_all"] = "OK"
    except Exception as e:
        results["create_all"] = f"ERROR: {str(e)}\n{traceback.format_exc()}"
        
    return results

@router.get("/api/admin/schema")
def get_schema(db: Session = Depends(get_db)):
    from sqlalchemy import text
    query = text("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = 'prediction_records'
        ORDER BY ordinal_position;
    """)
    result = db.execute(query).fetchall()
    return {"columns": [{"column_name": r[0], "data_type": r[1]} for r in result]}

# ----------------------------------------
# PASSENGER PORTAL APIs
# ----------------------------------------

import random
import math
from pydantic import BaseModel
from typing import Optional

class TripPlanRequestV2(BaseModel):
    source_id: str
    destination_id: str
    bus_capacity: Optional[int] = 60

from app.database.models import GTFSStop, GTFSTrip, GTFSStopTime, Route
from sqlalchemy.orm import aliased


from .services.routing_service import resolve_route_dynamic
from .services.raptor_service import plan_trip_raptor, check_repeated_stop_names, get_transit_data
from .services.raptor_helpers import convert_raptor_to_route_info
from .services.eta_service import calculate_eta
from .services.peak_hour_service import peak_hour_service
from .services.demand_prediction_service import demand_prediction_service
from .services.fleet_optimization_service import (
    fleet_optimization_service, compute_fleet_plan, compute_demand_metrics,
    DEFAULT_FLEET_SIZE_PER_ROUTE,
)
from .services.route_optimization_service import route_optimization_service
from .services.fare_service import fare_service

def get_fleet_optimization_math(predicted_demand: int, capacity: int = 60) -> dict:
    if predicted_demand <= 0:
        return {"buses_required": 0, "utilization": 0.0}
    buses_required = math.ceil(predicted_demand / capacity)
    utilization = (predicted_demand / (buses_required * capacity)) * 100.0
    return {
        "buses_required": buses_required,
        "utilization": round(utilization, 2)
    }


@router.post("/api/plan_trip")
def plan_trip(req: TripPlanRequestV2, request: Request, db: Session = Depends(get_db)):
    """
    Transit trip planner — Google Maps Transit style.

    Returns:
        route path, distance, physics-based ETA,
        live buses on route, occupancy, service frequency, next arrivals.

    Does NOT:
        Perform routing algorithms (delegated to maps/GTFS).
    """
    db, should_close = resolve_db_session(db)
    
    # Check if the requester is an admin
    is_admin = False
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        try:
            payload = decode_access_token(token)
            if payload and payload.get("role") in ["Admin", "Operator"]:
                is_admin = True
        except Exception:
            pass
    t0 = time.time()
    app_logger.info(
        f"Trip request received: "
        f"source={req.source_id}, "
        f"destination={req.destination_id}"
    )
    
    # Resolve stop names with canonicalization
    source_stop = db.query(GTFSStop).filter(GTFSStop.stop_id == req.source_id).first()
    destination_stop = db.query(GTFSStop).filter(GTFSStop.stop_id == req.destination_id).first()
    
    app_logger.info(
        "STOP_TRACE_1_INPUT_STOPS",
        extra={
            "extra_data": {
                "stage": "input_stops",
                "source_id": str(req.source_id),
                "destination_id": str(req.destination_id),
                "source_stop_exists": source_stop is not None,
                "destination_stop_exists": destination_stop is not None,
            }
        }
    )
    
    # Canonicalize stop IDs if multiple stops share the same name
    from .services.routing_service import _canonicalize_stop_id
    canonical_source_id = req.source_id
    canonical_dest_id = req.destination_id
    
    if source_stop:
        canonical_source_id = _canonicalize_stop_id(db, source_stop.stop_name) or req.source_id
        if canonical_source_id != req.source_id:
            app_logger.info(
                "STOP_CANONICALIZATION_APPLIED",
                extra={
                    "extra_data": {
                        "stop_name": source_stop.stop_name,
                        "original_stop_id": str(req.source_id),
                        "canonical_stop_id": str(canonical_source_id)
                    }
                }
            )
    
    if destination_stop:
        canonical_dest_id = _canonicalize_stop_id(db, destination_stop.stop_name) or req.destination_id
        if canonical_dest_id != req.destination_id:
            app_logger.info(
                "STOP_CANONICALIZATION_APPLIED",
                extra={
                    "extra_data": {
                        "stop_name": destination_stop.stop_name,
                        "original_stop_id": str(req.destination_id),
                        "canonical_stop_id": str(canonical_dest_id)
                    }
                }
            )
    
    app_logger.info(
        "STOP_TRACE_2_CANONICALIZED_STOPS",
        extra={
            "extra_data": {
                "stage": "canonicalized_stops",
                "source_id": str(req.source_id),
                "canonical_source_id": str(canonical_source_id),
                "destination_id": str(req.destination_id),
                "canonical_dest_id": str(canonical_dest_id),
            }
        }
    )
    
    app_logger.info(
        "PIPELINE AUDIT - Stop Resolution",
        extra={
            "extra_data": {
                "stage": "stop_resolution",
                "source_id": str(req.source_id),
                "canonical_source_id": str(canonical_source_id),
                "source_stop_name": source_stop.stop_name if source_stop else "NOT_FOUND",
                "source_stop_lat": float(source_stop.stop_lat) if source_stop and source_stop.stop_lat else None,
                "source_stop_lon": float(source_stop.stop_lon) if source_stop and source_stop.stop_lon else None,
                "destination_id": str(req.destination_id),
                "canonical_dest_id": str(canonical_dest_id),
                "destination_stop_name": destination_stop.stop_name if destination_stop else "NOT_FOUND",
                "destination_stop_lat": float(destination_stop.stop_lat) if destination_stop and destination_stop.stop_lat else None,
                "destination_stop_lon": float(destination_stop.stop_lon) if destination_stop and destination_stop.stop_lon else None,
            }
        }
    )

    app_logger.info(
        "plan_trip request received",
        extra={
            "extra_data": {
                "endpoint": "plan_trip",
                "source_id": str(req.source_id),
                "destination_id": str(req.destination_id),
            }
        },
    )
    # Route Resolution — RAPTOR is now the default engine. Legacy Dijkstra
    # (routing_service.resolve_route_dynamic) is kept only as an explicit
    # opt-out via USE_RAPTOR=false; it should not be relied on in production —
    # see routing_service._transfer_aware_dijkstra for known scaling limits
    # on this dataset's route density.
    use_raptor = os.getenv("USE_RAPTOR", "true").lower() == "true"
    
    try:
        if use_raptor:
            app_logger.info("Using RAPTOR routing algorithm")
            # Convert current time to seconds since midnight for RAPTOR
            current_time = datetime.datetime.now()
            start_time_sec = current_time.hour * 3600 + current_time.minute * 60 + current_time.second
            
            raptor_result = plan_trip_raptor(
                db,
                canonical_source_id,
                canonical_dest_id,
                start_time_sec,
                max_transfers=3
            )
            
            route_info = convert_raptor_to_route_info(raptor_result, db)
        else:
            app_logger.info("Using Dijkstra routing algorithm")
            route_info = resolve_route_dynamic(
                db,
                canonical_source_id,
                canonical_dest_id,
                bus_capacity=(req.bus_capacity if req.bus_capacity else 60),
            )
    except HTTPException as e:
        if e.status_code == 404:
            app_logger.info(
                "plan_trip no route found",
                extra={
                    "extra_data": {
                        "endpoint": "plan_trip",
                        "source_id": str(req.source_id),
                        "destination_id": str(req.destination_id),
                        "status_code": 404,
                        "detail": str(e.detail),
                        "duration_ms": round((time.time() - t0) * 1000, 2),
                    }
                },
            )
            return {"success": False, "message": e.detail or "No route found"}
        app_logger.warning(
            "plan_trip HTTPException",
            extra={
                "extra_data": {
                    "endpoint": "plan_trip",
                    "source_id": str(req.source_id),
                    "destination_id": str(req.destination_id),
                    "status_code": int(e.status_code),
                    "detail": str(e.detail),
                    "duration_ms": round((time.time() - t0) * 1000, 2),
                }
            },
        )
        raise e
    except Exception as e:
        app_logger.exception(
            "plan_trip unexpected routing error",
            extra={
                "extra_data": {
                    "endpoint": "plan_trip",
                    "source_id": str(req.source_id),
                    "destination_id": str(req.destination_id),
                    "duration_ms": round((time.time() - t0) * 1000, 2),
                }
            },
        )
        raise HTTPException(status_code=500, detail=f"Routing engine failed: {str(e)}")

    app_logger.info(
        "PIPELINE AUDIT - Route Resolution Result",
        extra={
            "extra_data": {
                "stage": "route_resolution",
                "source_id": str(req.source_id),
                "destination_id": str(req.destination_id),
                "route_id": str(route_info.get("route_id")),
                "ml_route_id": str(route_info.get("ml_route_id")),
                "stops_count": int(len(route_info.get("stops", []) or [])),
                "stops_list": route_info.get("stops", [])[:10],  # First 10 stops
                "transfers_count": int(len(route_info.get("transfers", []) or [])),
                "transfers_list": route_info.get("transfers", [])[:5],  # First 5 transfers
                "total_distance_km": route_info.get("total_distance_km"),
                "route_ids": route_info.get("route_ids", []),
                "routing_duration_ms": round((time.time() - t0) * 1000, 2),
            }
        },
    )

    # ── Post-routing pipeline ─────────────────────────────────────────────────
    # 3. Environmental State (weather + traffic from scheduler cache / DB)
    from app.database.models import WeatherRecord
    latest_weather   = db.query(WeatherRecord).order_by(WeatherRecord.timestamp.desc()).first()
    if latest_weather:
        weather_condition = latest_weather.condition
        weather_full      = f"{weather_condition}, {latest_weather.temperature}\u00b0C"
    else:
        weather_full      = app_cache.get("weather") or "Clear, 28.0\u00b0C"
        weather_condition = weather_full.split(",")[0].strip()

    traffic_state = app_cache.get("traffic") or "Medium"
    current_hour  = datetime.datetime.now().hour

    # Calculate distance first (needed for features)
    total_stops       = len(route_info["stops"])
    total_distance_km = route_info.get("total_distance_km")
    distance_available = True
    if not total_distance_km or total_distance_km <= 0:
        total_distance_km = 0.0
        distance_available = False
        app_logger.warning(f"Route distance was zero/None - distance_available set to false")

    bus_cap = req.bus_capacity if req.bus_capacity else 60

    # 5. Peak-Hour Detection (needed before prediction for features)
    peak_result  = peak_hour_service.detect_peak_hour(current_hour)
    peak_status  = peak_result["peak_status"]

    # 4. Demand Prediction (ML model with CatBoost)
    # Build complete feature set for CatBoost model
    current_dt = datetime.datetime.now()
    route_id = route_info.get("route_id", "default")

    # ── Historical demand baseline ────────────────────────────────────────────
    # Strategy:
    #   1. Try each route_id on the trip (multi-leg trips have several).
    #   2. If still no DB hit, estimate from route distance + stop count so
    #      different trips produce meaningfully different demand baselines
    #      (instead of every route collapsing to the flat 45.0 default).
    from app.database.models import DemandHistory
    from sqlalchemy.sql import func

    all_route_ids = list(route_info.get("route_ids", [])) or [route_id]
    historical_route_average: float = 0.0

    try:
        for rid in all_route_ids:
            avg_val = db.query(func.avg(DemandHistory.passenger_count)).filter(
                DemandHistory.route_id == rid
            ).scalar()
            if avg_val:
                historical_route_average = float(avg_val)
                app_logger.info(f"DemandHistory hit: route={rid} avg={historical_route_average:.1f}")
                break
    except Exception as _demand_history_err:
        app_logger.warning(f"DemandHistory query failed: {_demand_history_err}")
        db.rollback()

    if historical_route_average == 0.0:
        # Proxy: longer routes / more stops generally serve more passengers.
        # Base of 30 pax + 1.5 pax per km + 0.5 pax per stop, capped at 150.
        _dist   = float(total_distance_km or 5.0)
        _stops  = int(len(route_info.get("stops", [])) or 10)
        _transfers = int(len(route_info.get("transfers", [])) or 0)
        historical_route_average = min(150.0, 30.0 + (_dist * 1.5) + (_stops * 0.5) + (_transfers * 5.0))
        app_logger.info(
            f"DemandHistory miss for routes {all_route_ids} — "
            f"using proxy baseline: dist={_dist:.1f}km stops={_stops} "
            f"transfers={_transfers} → baseline={historical_route_average:.1f}"
        )

    is_peak = 1 if current_hour in [7, 8, 9, 17, 18, 19] else 0
    time_mult    = 1.8 if is_peak else 0.7 if current_hour in [22, 23, 0, 1, 2, 3, 4, 5] else 1.0
    weather_mult = 0.8 if weather_condition.lower() in ["rain", "rainy", "storm"] else 1.0
    traffic_mult = 1.3 if traffic_state == "Heavy" else 1.15 if traffic_state == "High" else 1.0

    adjusted_demand = historical_route_average * time_mult * weather_mult * traffic_mult

    historical_hour_average    = adjusted_demand
    historical_stop_average    = historical_route_average * 0.8
    historical_peak_average    = historical_route_average * 1.8
    historical_weekend_average = historical_route_average * 0.6

    boarding_count     = max(1, int(adjusted_demand * 0.55))
    alighting_count    = max(1, int(adjusted_demand * 0.45))
    onboard_passengers = boarding_count + alighting_count

    traffic_factor    = 1.0 if traffic_state == "Medium" else 1.5 if traffic_state == "High" else 0.8
    route_distance_km = total_distance_km if total_distance_km else 5.0

    # Route popularity: normalise distance into a 0.1–1.0 score
    route_popularity_score = min(1.0, max(0.1, route_distance_km / 50.0))

    # Calculate occupancy and load factor
    occupancy_ratio = min(1.0, onboard_passengers / (bus_cap if bus_cap else 60))
    load_factor     = occupancy_ratio
    demand_class    = "High" if load_factor > 0.8 else "Medium" if load_factor > 0.4 else "Low"

    traffic_delay = int(route_distance_km * traffic_factor)
    weather_delay = 5 if weather_condition.lower() in ["rain", "rainy", "storm"] else 0
    total_delay   = traffic_delay + weather_delay
    features = {
        "service_date": int(current_dt.strftime("%Y%m%d")),
        "route_id": route_id,
        "route_short_name": route_id[:10] if len(route_id) > 10 else route_id,
        "route_type": 3,
        "service_id": "default",
        "trip_id": f"trip_{route_id}_{current_hour}",
        "shape_id": f"shape_{route_id}",
        "direction_id": 0,
        "stop_id": req.source_id,
        "stop_name": source_stop.stop_name if source_stop else "Unknown",
        "stop_sequence": 1,
        "stop_lat": float(source_stop.stop_lat) if source_stop and source_stop.stop_lat else 0.0,
        "stop_lon": float(source_stop.stop_lon) if source_stop and source_stop.stop_lon else 0.0,
        "terminal_stop_flag": 0,
        "major_interchange_flag": 1 if source_stop and "Interchange" in source_stop.stop_name else 0,
        "area_type": "Mixed",
        "cumulative_distance": 0.0,
        "remaining_distance": total_distance_km if total_distance_km else 0.0,
        "number_of_stops": len(route_info.get("stops", [])),
        "remaining_stops": len(route_info.get("stops", [])),
        "route_length_km": total_distance_km if total_distance_km else 0.0,
        "scheduled_trip_duration": int(((total_distance_km or 0) / 30.0) * 60),
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
        "traffic_delay": traffic_delay,
        "weather_delay": weather_delay,
        "boarding_delay": 0,
        "total_delay": total_delay,
        "headway_minutes": 15,
        "service_frequency_category": "Normal",
        "historical_route_average": historical_route_average,
        "historical_stop_average": historical_stop_average,
        "historical_hour_average": historical_hour_average,
        "historical_peak_average": historical_peak_average,
        "historical_weekend_average": historical_weekend_average,
        "route_popularity_score": route_popularity_score,
        "vehicle_capacity": bus_cap,
        "boarding_count": boarding_count,
        "alighting_count": alighting_count,
        "onboard_passengers": onboard_passengers,
        "occupancy_ratio": occupancy_ratio,
        "load_factor": load_factor,
        "demand_class": demand_class,
    }

    app_logger.info(
        "PIPELINE AUDIT - Feature Generation",
        extra={
            "extra_data": {
                "stage": "feature_generation",
                "source_id": str(req.source_id),
                "destination_id": str(req.destination_id),
                "route_id": route_id,
                "feature_count": len(features),
                "key_features": {
                    "route_id": features["route_id"],
                    "hour": features["hour"],
                    "day_of_week": features["day_of_week"],
                    "weather_condition": features["weather_condition"],
                    "traffic_level": features["traffic_level"],
                    "peak_hour_flag": features["peak_hour_flag"],
                    "route_length_km": features["route_length_km"],
                    "vehicle_capacity": features["vehicle_capacity"],
                }
            }
        }
    )
    
    app_logger.info(f"DEMAND_TRACE: Generated feature vector for route {route_id}: {features}")

    # Calculate segment_ratio before calling ML prediction
    journey_stops = len(route_info.get("stops", []))
    total_route_stops = route_info.get("total_stops_on_route", max(journey_stops, 10))
    segment_ratio = max(0.1, min(1.0, journey_stops / total_route_stops))

    # Call ML prediction service with CatBoost
    app_logger.info(f"Calling demand prediction service for route {route_id}")
    prediction_result = demand_prediction_service.predict(features, segment_ratio=segment_ratio)
    
    route_demand = prediction_result.get("route_predicted_passengers", 0)
    journey_demand = prediction_result.get("journey_predicted_passengers", 0)
    demand_confidence = prediction_result.get("confidence", 0.97)
    model_source = prediction_result.get("model_source", "catboost")
    demand_class = prediction_result.get("demand_class", "Medium")
    
    # Keep legacy variable for other parts of the route that might still rely on it loosely
    predicted_demand = journey_demand if model_source == "catboost" else route_demand
    
    app_logger.info(
        f"ML Prediction: route_demand={route_demand} journey_demand={journey_demand} passengers, "
        f"confidence={demand_confidence:.3f}, source={model_source}"
    )

    app_logger.info(
        "PIPELINE AUDIT - CatBoost Prediction Result",
        extra={
            "extra_data": {
                "stage": "catboost_prediction",
                "source_id": str(req.source_id),
                "destination_id": str(req.destination_id),
                "route_id": route_id,
                "route_demand": route_demand,
                "journey_demand": journey_demand,
                "demand_confidence": demand_confidence,
                "model_source": model_source,
                "demand_class": demand_class,
            }
        }
    )

    app_logger.info(f"DEMAND_TRACE: Raw CatBoost prediction for {route_id}: {prediction_result}")

    # 6. Forecast Demand (next hour for trend calculation using CatBoost)
    next_hour = (current_hour + 1) % 24
    forecast_features = features.copy()
    forecast_features["hour"] = next_hour
    forecast_features["trip_id"] = f"trip_{route_id}_{next_hour}"
    forecast_features["trip_start_time"] = next_hour * 60
    forecast_features["trip_end_time"] = (next_hour + 1) * 60
    forecast_features["time_slot"] = "Morning" if next_hour < 12 else "Afternoon" if next_hour < 17 else "Evening"
    
    forecast_result = demand_prediction_service.predict(forecast_features, segment_ratio=segment_ratio)
    forecast_demand = forecast_result.get("route_predicted_passengers", 0) # Forecast usually cares about route-wide trend

    # 7. Demand Prediction Engine
    demand_available = True
    if route_demand == 0 and journey_demand == 0:
        demand_available = False
        demand_passengers = 0
        demand_score = 0
        demand_confidence = 0.0
        app_logger.warning(f"CatBoost prediction returned 0 for route {route_id}")
    else:
        demand_available = True
        
        # APPROXIMATION: segment_ratio = journey_stops / total_route_stops.
        # This is a linear proportionality assumption and will overestimate route demand
        # for routes where demand is clustered at specific stops (e.g. terminals).
        # Replace with a trained segment-demand model when labelled segment data is available.

        demand_passengers = route_demand
        demand_score = min(100, int((route_demand / MAX_PASSENGERS) * 100))
        demand_confidence = float(demand_confidence)

    # 8. Route Optimization Engine
    route_opt_result = route_optimization_service.optimize(
        route_path = route_info.get("route_path", []),
        traffic    = traffic_state,
        weather    = weather_condition,
        transfers  = len(route_info.get("transfers", []))
    )
    route_efficiency = route_opt_result["route_efficiency"]

    # 9. Physics-Based ETA (with peak & weather confidence)
    eta_result = calculate_eta(
        total_distance_km  = total_distance_km,
        predicted_demand   = demand_passengers,
        bus_cap            = bus_cap,
        traffic_state      = traffic_state,
        weather_condition  = weather_condition,
        peak_status        = peak_status,
    )
    eta_minutes       = eta_result["eta_minutes"]
    delay_minutes     = eta_result["delay_minutes"]
    occupancy         = eta_result["occupancy"]
    confidence_score  = eta_result["eta_confidence"]

    # ETA occupancy is purely used for delay physics — not surfaced as demand metric.
    
    # 7. Service Frequency + Fleet Sizing — single source of truth
    #    compute_demand_metrics() is the ONLY place that computes required_buses,
    #    allocated_buses, and the resulting headway.  The old schedule-engine cache
    #    lookup, the two fleet-optimization override blocks, and the TTL-cycle-time
    #    block have all been removed; they all produced different allocated_buses
    #    values that could diverge from what gets persisted in OptimizationResult.
    dm = compute_demand_metrics(
        route_predicted_passengers=route_demand,
        journey_predicted_passengers=journey_demand,
        available_buses=DEFAULT_FLEET_SIZE_PER_ROUTE,
        bus_capacity=bus_cap,
        is_peak=bool(is_peak),
    )

    # Derive route_freq exclusively from dm so the passenger dashboard, the
    # admin dashboard, and the OptimizationResult row all read the same number.
    _allocated = max(1, dm["allocated_buses"])
    _headway   = max(5, 60 // _allocated)
    _tier      = "High" if _allocated >= 4 else "Medium" if _allocated >= 2 else "Low"
    _label     = "Peak Frequency" if bool(is_peak) else "Off-Peak Frequency"
    _now       = datetime.datetime.now()
    _arrivals  = [
        {
            "bus_number": i,
            "arrival_time": (_now + datetime.timedelta(minutes=_headway * i)).strftime("%I:%M %p"),
        }
        for i in range(1, _allocated + 1)
    ]
    route_freq = {
        "buses_per_hour":  _allocated,
        "headway_minutes": _headway,
        "frequency_tier":  _tier,
        "label":           _label,
        "is_peak":         bool(is_peak),
        "next_arrivals":   _arrivals,
    }

    service_frequency = {
        "buses_per_hour":  route_freq["buses_per_hour"],
        "headway_minutes": route_freq["headway_minutes"],
        "frequency_tier":  route_freq["frequency_tier"],
        "label":           route_freq["label"],
        "is_peak":         route_freq["is_peak"],
        "next_arrivals":   route_freq["next_arrivals"],
    }
    next_arrivals = route_freq["next_arrivals"]

    app_logger.info(
        "NEXT_ARRIVALS_DEBUG",
        extra={
            "extra_data": {
                "route_id": route_info.get("route_id"),
                "buses_per_hour": route_freq["buses_per_hour"],
                "headway_minutes": route_freq["headway_minutes"],
                "is_peak": route_freq["is_peak"],
                "allocated_buses": dm["allocated_buses"],
                "capacity_required_buses": dm["capacity_required_buses"],
                "frequency_required_buses": dm["frequency_required_buses"],
                "next_arrivals_count": len(next_arrivals),
                "next_arrivals": next_arrivals,
            }
        }
    )

    demand_level = dm["demand_level"]
    demand_level_for_log = dm["demand_level"]

    print("\n" + "="*50)
    print("ROUTE-SPECIFIC DIAGNOSTIC AUDIT")
    print(f"- source stop: {req.source_id}")
    print(f"- destination stop: {req.destination_id}")
    print(f"- selected route_id: {route_id}")
    print(f"- prediction source: {model_source}")
    # Reverse engineer raw CatBoost prediction
    raw_pred = journey_demand if model_source == "catboost" else route_demand
    print(f"- raw prediction: {raw_pred}")
    print(f"- journey_predicted_passengers: {journey_demand}")
    print(f"- route_predicted_passengers: {route_demand}")
    print(f"- journey_stops: {journey_stops}")
    print(f"- total_route_stops: {total_route_stops}")
    print(f"- segment_ratio: {segment_ratio:.4f}")
    print(f"- required_buses: {dm['required_buses']}")
    print(f"- allocated_buses: {dm['allocated_buses']}")
    print(f"- available_buses: {dm['available_buses']}")
    print(f"- bus_capacity: {bus_cap}")
    print(f"- occupancy_percentage: {dm['operational_occupancy_pct']}%")
    print(f"- crowd_level: {dm['crowd_level']}")
    print(f"- demand_level: {dm['demand_level']}")
    print("="*50 + "\n")
    # -----------------------------------------------

    app_logger.info("OPTIMIZATION_METHOD_START: Calling rule-based compute_fleet_plan")
    
    # compute_fleet_plan is still used for headway/frequency_adjustment logic,
    # but fleet allocation numbers come exclusively from dm (DemandMetrics).
    fleet_recommendation = compute_fleet_plan(
        route_data={
            "route_id": route_info.get("route_id"),
            "bus_capacity": bus_cap,
            "current_buses": route_freq.get("buses_per_hour", 1),
            "occupancy_percent": dm["operational_occupancy_pct"],
            "headway_minutes": route_freq.get("headway_minutes"),
            "total_distance_km": total_distance_km,
        },
        demand_data={
            "route_predicted_passengers": dm["route_predicted_passengers"],
            "demand_score": demand_score,
            "confidence": demand_confidence,
        },
    )

    # 8. Live Bus Registration - use vehicle_tracking_service to retrieve assigned vehicle
    from app.services.vehicle_tracking_service import vehicle_tracking_service
    
    # Try to find an existing active vehicle for this route
    active_buses = vehicle_tracking_service.get_all_active_vehicles()
    route_buses = [b for b in active_buses if b["route_id"] == route_info["route_id"]]
    
    if route_buses:
        bus_id = route_buses[0]["bus_id"]
    else:
        # No vehicle assigned - return null instead of synthetic ID
        bus_id = None

    # Fetch actual route numbers from the database to replace internal route IDs
    from app.database.models import Route
    route_display_names = ""
    r_ids = route_info.get("route_ids", [])
    if not r_ids and route_info.get("route_id"):
        r_ids = [route_info["route_id"]]
    
    if r_ids:
        db_routes = db.query(Route).filter(Route.route_id.in_([str(r) for r in r_ids])).all()
        # Create a map for quick lookup to maintain order
        route_map = {r.route_id: (r.route_short_name or r.name or r.route_id) for r in db_routes}
        names = [str(route_map.get(str(r_id), r_id)) for r_id in r_ids]
        route_display_names = " \u2192 ".join(names)

    app_logger.info(
        f"Trip planned | {route_info.get('source_name', req.source_id)} \u2192 {route_info.get('dest_name', req.destination_id)} | "
        f"route={route_info['route_id']} | stops={total_stops} | "
        f"dist={total_distance_km}km | ETA={eta_minutes}m | "
        f"freq={service_frequency['buses_per_hour']} bus/h | "
        f"traffic={traffic_state} | weather={weather_condition}"
    )

    # ── Clean API Response ──────────────────────────────────────────────
    app_logger.info(
        "PIPELINE AUDIT - Fleet Optimization",
        extra={
            "extra_data": {
                "stage": "fleet_optimization",
                "source_id": str(req.source_id),
                "destination_id": str(req.destination_id),
                "route_id": route_info["route_id"],
                "predicted_demand": predicted_demand,
                "bus_capacity": bus_cap,
                "current_fleet": route_freq.get("buses_per_hour", 1),
                "recommended_fleet": fleet_recommendation.get("buses_required", 1),
                "fleet_utilization": fleet_recommendation.get("utilization_score", 0) * 100,
            }
        }
    )

    app_logger.info(
        f"DEMAND_TRACE:\n"
        f"Route: {req.source_id} -> {req.destination_id}\n"
        f"Features generated: {len(features)}\n"
        f"Raw CatBoost prediction: {prediction_result}\n"
        f"Predicted demand: {predicted_demand}\n"
        f"Forecast demand: {forecast_demand}\n"
        f"Recommended buses: {fleet_recommendation.get('buses_required', 1)}\n"
        f"Utilization score: {fleet_recommendation.get('utilization_score', 0)}"
    )

    app_logger.info(
        "PIPELINE AUDIT - Final API Response",
        extra={
            "extra_data": {
                "stage": "final_response",
                "source_id": str(req.source_id),
                "destination_id": str(req.destination_id),
                "route_id": route_info["route_id"],
                "predicted_demand": predicted_demand if demand_available else None,
                "forecast_demand": forecast_demand if demand_available else None,
                "demand_available": demand_available,
                "occupancy_percent": occupancy,
                "eta_min": eta_minutes,
                "transfers_count": len(route_info.get("transfers", [])),
                "total_distance_km": total_distance_km,
                "peak_status": peak_status,
                "weather_condition": weather_condition,
                "traffic_state": traffic_state,
            }
        }
    )

    app_logger.info(
        "plan_trip completed",
        extra={
            "extra_data": {
                "endpoint": "plan_trip",
                "source_id": str(req.source_id),
                "destination_id": str(req.destination_id),
                "route_id": str(route_info.get("route_id")),
                "status": "success",
                "duration_ms": round((time.time() - t0) * 1000, 2),
            }
        },
    )
    # ── Calculate Expected Waiting Time ─────────────────────────────────
    # Use next_arrivals if available, otherwise use half of headway
    expected_waiting_time = max(1, int(route_freq.get("headway_minutes", 10) / 2))
    if next_arrivals and len(next_arrivals) > 0:
        try:
            now = datetime.datetime.now()
            # Handle both string format and object format
            if isinstance(next_arrivals[0], str):
                arrival_str = next_arrivals[0]
            elif isinstance(next_arrivals[0], dict) and next_arrivals[0].get("arrival_time"):
                arrival_str = next_arrivals[0]["arrival_time"]
            else:
                arrival_str = None
            
            if arrival_str:
                next_bus_time = datetime.datetime.strptime(arrival_str, "%I:%M %p")
                next_bus_time = next_bus_time.replace(year=now.year, month=now.month, day=now.day)
                if next_bus_time < now:
                    next_bus_time += datetime.timedelta(days=1)
                wait_seconds = (next_bus_time - now).total_seconds()
                expected_waiting_time = max(1, int(math.ceil(wait_seconds / 60)))
        except Exception as e:
            app_logger.warning(f"Failed to calculate waiting time from next_arrivals: {e}")
            expected_waiting_time = max(1, int(route_freq.get("headway_minutes", 10) / 2))

    app_logger.info(
        "WAITING_TIME_DEBUG",
        extra={
            "extra_data": {
                "route_id": route_info.get("route_id"),
                "headway_minutes": route_freq.get("headway_minutes"),
                "next_arrivals": next_arrivals,
                "expected_waiting_time": expected_waiting_time,
            }
        }
    )

    response_payload = {
        "success":                True,
        "source":                 route_info.get("source_name", req.source_id),
        "destination":            route_info.get("dest_name", req.destination_id),
        "route_id":               route_display_names or route_info["route_id"],
        "bus_id":                 bus_id,
        "path":                   route_info.get("path", route_info.get("route_path", [])),
        "distance_km":            total_distance_km if distance_available else "Unavailable",
        "distance_available":     distance_available,
        "demand_available":       demand_available,
        "transfers":              route_info.get("transfers", []),
        "eta_min":                eta_minutes,
        "fare":                   fare_service.calculate_fare(route_info["route_id"], total_distance_km if distance_available else 5.0),
        "route_ids":              route_info.get("route_ids", []),
        "debug":                  route_info.get("debug", {
            "graph_type": "MultiDiGraph",
            "edge_mode": "best_edge_only",
            "validated": True,
        }),

        # ─ Legacy compatibility fields ───────────────────────────────
        "estimated_travel_time":  eta_minutes,
        "expected_delay_minutes": delay_minutes,
        # occupancy_percent exposed as the operational figure (may exceed 100% in shortage)
        "occupancy_percent":      dm["operational_occupancy_pct"],
        "ideal_occupancy_pct":    dm["ideal_occupancy_pct"],
        "crowd_level":            dm["crowd_level"],
        "comfort_level":          dm["comfort_level"],
        "route_efficiency":       route_efficiency,

        # ─ Service Frequency ─────────────────────────────────────────
        "service_frequency":      service_frequency,
        "next_arrivals":          next_arrivals,
        "fleet_recommendation":   fleet_recommendation,

        # ─ Live Buses ────────────────────────────────────────────────
        "live_buses": [
            {
                "bus_id":            bus_id,
                "route_id":          route_info["route_id"],
                "current_location":  route_info["stops"][0] if route_info["stops"] else "En-Route",
                "status":            "In Transit",
                "occupancy_percent": occupancy,
                "eta_minutes":       eta_minutes,
            }
        ] if bus_id else [],
        "next_arrival_time": (
            datetime.datetime.now() + datetime.timedelta(minutes=route_freq["headway_minutes"])
        ).strftime("%I:%M %p"),

        # ─ Route Details ─────────────────────────────────────────────
        "stops":             route_info["stops"],
        "total_stops":       total_stops,
        "stop_sequence":     route_info["stops"],
        "route_legs":        route_info.get("route_legs", []),
        "route_path":        route_info.get("route_path", []),
        "total_distance_km": total_distance_km,
        "transfers":         route_info.get("transfers", []),

        # ─ Context ───────────────────────────────────────────────────
        "context": {
            "weather":      weather_full,
            "traffic":      traffic_state,
            "demand_level": demand_level,
        },
        "weather": weather_full,
        "traffic": traffic_state,

        # ─ AI Transit Intelligence ────────────────────────────────────
        "peak_status": peak_status,

        # ─ Fleet Optimization (Passenger Facing) ────────────────────────
        "expected_waiting_time": expected_waiting_time,

        # ─ AI Travel Recommendation (ETA/weather/comfort context) ──────────
        "ai_recommendation": fleet_optimization_service.generate_passenger_recommendation(
            eta_minutes=eta_minutes,
            transfers=len(route_info.get("transfers", [])),
            occupancy_percent=int(dm["operational_occupancy_pct"]),
            traffic_state=traffic_state,
            weather_condition=weather_condition,
            peak_status=peak_status,
            has_alternatives=False,
        ),
        "recommendation_reason": f"Based on {dm['journey_predicted_passengers']} journey predicted passengers and {dm['ideal_occupancy_pct']:.0f}% ideal occupancy",
        "recommendation_confidence": f"{demand_confidence:.2f}" if demand_available else "Medium",

        # ─ Route Selection ─────────────────────────────────────────────
        "selection_reason": f"Optimal route with {len(route_info.get('transfers', []))} transfer(s), {route_efficiency:.0f}% efficiency, and {demand_level} demand",
    }
    
    # Always include operational metrics for Admin Dashboard (JWT validation may fail but admin users need these values)
    response_payload.update({
        "predicted_demand": predicted_demand if demand_available else 0,
        "forecast_demand": forecast_demand if demand_available else 0,
        "demand_confidence": f"{demand_confidence:.2f}" if demand_available else "Unavailable",
        "current_fleet":         dm["available_buses"],
        "recommended_fleet":     dm["required_buses"],
        "required_buses":        dm["required_buses"],
        "allocated_buses":       dm["allocated_buses"],
        "additional_buses":      dm["additional_buses_needed"],
        "fleet_gap":             dm["fleet_gap"],
        "fleet_utilization":     dm["ideal_occupancy_pct"],
        "optimized_frequency":   fleet_recommendation.get("frequency_adjustment", "stable"),
        "optimization_status":   dm["allocation_status"].capitalize(),
        "fleet_recommendation_text": dm["fleet_recommendation"],
        "occupancy_percent": occupancy,
        "crowd_level": dm["crowd_level"],
        "bus_capacity": bus_cap
    })
    

    response_payload["debug_metadata"] = {
            "matched_source_stop":      req.source_id,
            "matched_destination_stop": req.destination_id,
            "normalization_status":     "removed_for_id_routing",
        }

    invalid_response_fields = []
    if not response_payload.get("path"):
        invalid_response_fields.append("path")

    distance_km = response_payload.get("distance_km")
    try:
        if float(distance_km) <= 0:
            invalid_response_fields.append("distance_km")
    except Exception:
        invalid_response_fields.append("distance_km")

    eta_min = response_payload.get("eta_min")
    try:
        if int(eta_min) < 1:
            invalid_response_fields.append("eta_min")
    except Exception:
        invalid_response_fields.append("eta_min")

    if invalid_response_fields:
        app_logger.warning(
            "plan_trip response safety check failed",
            extra={
                "extra_data": {
                    "endpoint": "plan_trip",
                    "source_id": str(req.source_id),
                    "destination_id": str(req.destination_id),
                    "invalid_fields": invalid_response_fields,
                }
            },
        )

    # ── Route efficiency KPI logging (for system-level dashboards) ───────────
    # This is the authoritative source for route efficiency KPIs (no mocked values).
    try:
        transfers_list = response_payload.get("transfers", [])
        transfers_count = len(transfers_list) if isinstance(transfers_list, list) else None
        crud.create_route_plan_log(
            db=db,
            route_id=str(route_info.get("route_id")) if route_info.get("route_id") else None,
            source_stop_id=str(req.source_id),
            destination_stop_id=str(req.destination_id),
            route_efficiency=int(route_efficiency),
            transfers_count=transfers_count,
            eta_minutes=float(eta_minutes) if eta_minutes is not None else None,
            traffic=str(traffic_state) if traffic_state else None,
            weather=str(weather_condition) if weather_condition else None,
        )
    except Exception as log_err:
        app_logger.warning(f"Failed to write RoutePlanLog (non-blocking): {log_err}")

    # ── Persist optimization results to database ───────────────────────────
    # This ensures the Admin Overview "Allocated Buses" card reflects real data
    try:
        # Debug logging to see all demand metrics values
        app_logger.info(
            "DEMAND_METRICS_DEBUG",
            extra={
                "extra_data": {
                    "route_id": route_info.get("route_id"),
                    "journey_demand": journey_demand,
                    "route_demand": route_demand,
                    "allocated_buses": dm.get("allocated_buses"),
                    "required_buses": dm.get("required_buses"),
                    "available_buses": dm.get("available_buses"),
                    "bus_capacity": bus_cap,
                    "ideal_occupancy_pct": dm.get("ideal_occupancy_pct"),
                    "operational_occupancy_pct": dm.get("operational_occupancy_pct"),
                    "fleet_gap": dm.get("fleet_gap"),
                    "demand_level": dm.get("demand_level"),
                }
            }
        )
        
        # Ensure allocated_buses is at least 1 if there's any demand
        final_allocated_buses = dm["allocated_buses"]
        if final_allocated_buses == 0 and int(journey_demand) > 0:
            final_allocated_buses = max(1, int(journey_demand / bus_cap) + (1 if journey_demand % bus_cap > 0 else 0))
            app_logger.warning(f"Overriding allocated_buses from 0 to {final_allocated_buses} based on demand {journey_demand}")
        
        # Use actual route_id from composite route to avoid FOREIGN KEY constraint
        # For composite routes, use the first route_id from route_ids list
        route_ids_list = route_info.get("route_ids", [])
        actual_route_id = str(route_ids_list[0]) if route_ids_list else str(route_info.get("route_id", ""))
        
        crud.create_optimization_result(
            db=db,
            route_id=actual_route_id,
            route_name=route_display_names or route_info.get("route_id", ""),
            allocated_buses=final_allocated_buses,
            utilization=dm["ideal_occupancy_pct"],
            objective_score=route_efficiency,
            unserved_demand=dm["fleet_gap"] if dm["fleet_gap"] > 0 else 0,
            priority_level="HIGH" if dm["demand_level"] == "High" else "MEDIUM",
            recommended_frequency=f"{dm['available_buses']} buses/hour",
            predicted_demand=int(journey_demand),
            model_version=model_source,
        )
        app_logger.info(
            "OPTIMIZATION_RESULT_PERSISTED",
            extra={
                "extra_data": {
                    "route_id": actual_route_id,
                    "allocated_buses": final_allocated_buses,
                    "predicted_demand": int(journey_demand),
                    "utilization": dm["ideal_occupancy_pct"],
                }
            }
        )
    except Exception as opt_err:
        app_logger.error(f"Failed to persist optimization result (non-blocking): {opt_err}")
        db.rollback()

    # ── Auto-save journey history for authenticated users ───────────────────
    # Extract JWT from Authorization header (optional — unauthenticated OK)
    try:
        from app.database.models import User as UserModel
        auth_header = request.headers.get("Authorization", "")
        jwt_token = auth_header.removeprefix("Bearer ").strip() if auth_header.startswith("Bearer ") else None
        
        app_logger.info(
            "JOURNEY_HISTORY_SAVE_START",
            extra={
                "extra_data": {
                    "auth_header_present": bool(auth_header),
                    "auth_header_starts_with_bearer": auth_header.startswith("Bearer ") if auth_header else False,
                    "jwt_token_present": bool(jwt_token)
                }
            }
        )
        
        if jwt_token:
            jwt_payload = decode_access_token(jwt_token)
            
            app_logger.info(
                "JOURNEY_HISTORY_CURRENT_USER",
                extra={
                    "extra_data": {
                        "jwt_payload_present": bool(jwt_payload),
                        "jwt_payload": jwt_payload if jwt_payload else None
                    }
                }
            )
            
            if jwt_payload:
                username = jwt_payload.get("sub")
                db_user = db.query(UserModel).filter(UserModel.username == username).first()
                
                app_logger.info(
                    "JOURNEY_HISTORY_DB_USER",
                    extra={
                        "extra_data": {
                            "username": username,
                            "db_user_found": bool(db_user),
                            "db_user_id": db_user.id if db_user else None
                        }
                    }
                )
                
                if db_user:
                    # Build a human-readable route summary
                    route_ids_list = response_payload.get("route_ids", [])
                    if route_ids_list:
                        route_summary = " → ".join(str(r) for r in route_ids_list[:3])
                    else:
                        route_summary = str(route_info.get("route_id", ""))
                    transfers_list = response_payload.get("transfers", [])
                    transfer_count = len(transfers_list) if isinstance(transfers_list, list) else 0
                    
                    app_logger.info(
                        "JOURNEY_HISTORY_INSERT_DATA",
                        extra={
                            "extra_data": {
                                "user_id": db_user.id,
                                "source_stop_id": str(req.source_id),
                                "destination_stop_id": str(req.destination_id),
                                "route_summary": route_summary,
                                "transfer_count": transfer_count,
                                "estimated_duration": eta_minutes
                            }
                        }
                    )
                    
                    crud.create_journey_history(
                        db=db,
                        user_id=db_user.id,
                        source_stop_id=str(req.source_id),
                        source_stop_name=response_payload.get("source", str(req.source_id)),
                        destination_stop_id=str(req.destination_id),
                        destination_stop_name=response_payload.get("destination", str(req.destination_id)),
                        route_summary=route_summary,
                        transfer_count=transfer_count,
                        estimated_duration=eta_minutes,
                    )
                    
                    app_logger.info(
                        "JOURNEY_HISTORY_SAVE_SUCCESS",
                        extra={
                            "extra_data": {
                                "user_id": db_user.id,
                                "username": username
                            }
                        }
                    )
                else:
                    app_logger.warning(
                        "JOURNEY_HISTORY_DB_USER_NOT_FOUND",
                        extra={
                            "extra_data": {
                                "username": username
                            }
                        }
                    )
            else:
                app_logger.warning(
                    "JOURNEY_HISTORY_JWT_PAYLOAD_INVALID",
                    extra={
                        "extra_data": {
                            "jwt_token_present": bool(jwt_token)
                        }
                    }
                )
        else:
            app_logger.info(
                "JOURNEY_HISTORY_NO_JWT_TOKEN",
                extra={
                    "extra_data": {
                        "auth_header": auth_header[:50] if auth_header else ""
                    }
                }
            )

    except Exception as hist_err:
        # Never block the trip response due to history saving failure
        app_logger.error(
            "JOURNEY_HISTORY_SAVE_FAILED",
            extra={
                "extra_data": {
                    "error": str(hist_err)
                }
            }
        )

    app_logger.info(f"DEBUG: returning payload of type {type(response_payload)}, is None? {response_payload is None}")
    return response_payload

# /api/plan_trip_v2 removed — it used per-request DQL bus dispatch (Uber model).
# The system now uses city-level demand-based scheduling via /api/schedule_status.

@router.get("/api/admin/fleet-optimization")
def get_fleet_optimization(route_id: str = "ALL", request: Request = None, db: Session = Depends(get_db)):
    """
    Returns fleet optimization data for the Admin Dashboard.
    """
    # Simplified simulation based on request logic
    svc = getattr(request.app.state, "prediction_service", None)
    
    weather = app_cache.get("weather") or "Clear"
    traffic = app_cache.get("traffic") or "Medium"
    current_hour = datetime.datetime.now().hour
    
    if svc is not None and svc.model is not None:
        predicted_demand = svc.predict_demand(
            route_id=route_id,
            hour=current_hour,
            weather_condition=weather,
            traffic=traffic,
        )
    else:
        raise HTTPException(status_code=503, detail="Prediction model not loaded; cannot compute fleet optimization KPIs.")
        
    peak_result = peak_hour_service.detect_peak_hour(current_hour)
    peak_status = peak_result["peak_status"]
    
    bus_cap = 60
    demand_result = demand_prediction_service.predict_legacy(
        route_id       = route_id,
        passenger_count= predicted_demand,
        occupancy_percent= round((predicted_demand / bus_cap) * 100, 1),
        weather        = weather,
        traffic        = traffic,
        hour_of_day    = current_hour,
        day_of_week    = datetime.datetime.now().weekday(),
        peak_status    = peak_status,
    )
    demand_passengers = demand_result["route_predicted_passengers"]
    demand_confidence = round(demand_result["confidence"] * 100)
    
    fleet_result = fleet_optimization_service.optimize(
        route_predicted_passengers = demand_passengers,
        bus_capacity               = bus_cap,
    )
    
    utilization = fleet_result["fleet_utilization"]
    gap = fleet_result["fleet_gap"]
    req_fleet = fleet_result["required_buses"]
    avail_fleet = fleet_result["available_buses"]
    
    if gap > 0:
        rec = f"Allocate {gap} additional buses during peak hours. Expected occupancy exceeds threshold."
    elif gap < 0:
        rec = f"Reduce fleet by {abs(gap)} buses to save operational costs. Demand is low."
    else:
        rec = "No additional buses required. Current fleet allocation is sufficient."
        
    # System route efficiency KPI derived from actual route planning outcomes.
    # If there are no route plans logged yet, return None (no placeholder).
    try:
        from sqlalchemy import func
        from app.database.models import RoutePlanLog
        since = datetime.datetime.utcnow() - datetime.timedelta(days=1)
        avg_eff = (
            db.query(func.avg(RoutePlanLog.route_efficiency))
            .filter(RoutePlanLog.created_at >= since)
            .scalar()
        )
        route_efficiency_kpi = int(round(float(avg_eff))) if avg_eff is not None else None
    except Exception as e:
        app_logger.warning(f"Failed to compute route_efficiency KPI: {e}")
        route_efficiency_kpi = None

    return {
        "predicted_demand": demand_passengers,
        "demand_confidence": demand_confidence,
        "required_fleet": req_fleet,
        "available_fleet": avail_fleet,
        "fleet_gap": gap,
        "fleet_utilization": utilization,
        "route_efficiency": route_efficiency_kpi,
        "recommendation": rec
    }


@router.get("/api/alerts")
def get_service_alerts(request: Request):
    weather = app_cache.get('weather') or 'clear'
    traffic = app_cache.get('traffic') or 'medium'

    alerts = []

    if weather.lower().startswith('rainy'):
        alerts.append({"type": "Weather", "severity": "Medium", "title": "Heavy Rain Alert",
                        "message": "Expect delays across all routes due to heavy rainfall. Service frequency increased on affected routes."})
    if traffic.lower() in ['high', 'heavy']:
        alerts.append({"type": "Traffic", "severity": "High", "title": "High Traffic Alert",
                        "message": "Severe congestion detected. ETA computations adjusted. Bus frequency increased on peak routes."})

    # Check if schedule engine found peak-hour high-frequency routes
    schedule_status = app_cache.get("schedule_status")
    if schedule_status:
        high_freq_count = sum(
            1 for r in schedule_status.get("routes", []) if r.get("frequency_tier") == "HIGH"
        )
        if schedule_status.get("peak_active"):
            alerts.append({"type": "Schedule", "severity": "Info", "title": "Peak Hour Service Active",
                            "message": f"High-frequency service active on {high_freq_count} routes. Headway reduced to 8 min."})

    if not alerts:
        alerts.append({"type": "System", "severity": "Low", "title": "Normal Operations",
                        "message": "All transit systems are operating normally."})

    return alerts


@router.get("/api/schedule_status")
def get_schedule_status(request: Request):
    """
    Returns the current city-level service frequency for all routes.
    Data is produced by the demand-based schedule engine (batch job, every 10 min).
    This is a READ-ONLY observability endpoint — it does not dispatch buses.
    """
    status = app_cache.get("schedule_status")
    if not status:
        # Trigger an immediate on-the-fly compute if cache is cold
        from .services.schedule_engine import update_schedule_engine
        status = update_schedule_engine(
            app_state=getattr(request.app, "state", None),
            app_cache=app_cache,
        )
        if not status:
            return {
                "routes": [],
                "updated_at": None,
                "message": "Schedule engine warming up. Please retry in a moment.",
            }

    return status


# DQL endpoints removed:
#   /api/train_dql_model     — trained a per-request dispatch model (Uber pattern)
#   /api/predict_bus_allocation — assigned buses per user request (wrong model)
#
# The system now uses demand-based BATCH scheduling via the ScheduleEngine.
# Use /api/schedule_status to view current service frequencies per route.

# ─── Passenger Journey History ────────────────────────────────────────────────

from app.database.models import User as UserModel

@router.get("/api/passenger/history")
def get_passenger_history(
    request: Request,
    page: int = 1,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_passenger),
):
    """
    Returns paginated journey history for the authenticated passenger.
    Records are inserted automatically whenever POST /api/plan_trip succeeds.
    """
    if page < 1:
        page = 1
    if limit < 1 or limit > 100:
        limit = 20

    username = current_user.get("sub")
    db_user = db.query(UserModel).filter(UserModel.username == username).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    total, items = crud.get_journey_history(db=db, user_id=db_user.id, page=page, limit=limit)

    serialized = [
        {
            "id": str(item.id),
            "source_stop_id": item.source_stop_id,
            "source_stop_name": item.source_stop_name,
            "destination_stop_id": item.destination_stop_id,
            "destination_stop_name": item.destination_stop_name,
            "route_summary": item.route_summary,
            "transfer_count": item.transfer_count,
            "estimated_duration": item.estimated_duration,
            "created_at": item.created_at.isoformat() if item.created_at else None,
        }
        for item in items
    ]

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "items": serialized,
    }


# --- System Monitoring Endpoint ---

@router.get("/api/system/metrics")
def get_system_metrics(user = Depends(verify_admin)):
    try:
        import psutil
        return {
            "cpu_usage":       psutil.cpu_percent(interval=None),
            "memory_usage":    psutil.virtual_memory().percent,
            "disk_usage":      psutil.disk_usage('/').percent,
            "active_threads":  psutil.Process().num_threads(),
        }
    except ImportError:
        return {
            "cpu_usage": "Unavailable",
            "memory_usage": "Unavailable",
            "disk_usage": "Unavailable",
            "active_threads": "Unavailable",
            "error": "psutil not installed"
        }

@router.post("/api/admin/run-optimization")
def run_optimization_manual(request: Request, db: Session = Depends(get_db)):
    from app.services.optimization_engine import OptimizationEngine

    app_logger.info("Manual optimization run requested")
    
    try:
        response = OptimizationEngine.run(db=db)
        return {
            "success": True,
            "routes_processed": len(response.allocated_buses),
            "rows_inserted": len(response.allocated_buses)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))