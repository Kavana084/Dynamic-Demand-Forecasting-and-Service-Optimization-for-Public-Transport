import random
from apscheduler.schedulers.background import BackgroundScheduler
import time
from .logger import app_logger
from .cache import app_cache
from app.database.connection import SessionLocal
from app.database.models import WeatherRecord

import requests
import datetime
from .services.demand_aggregation_service import demand_aggregation_service
from app.database.crud import create_prediction

# Global scheduler instance
scheduler = BackgroundScheduler()

# Shared app_state reference — set by main.py after startup
_app_state = None

def set_app_state(state):
    """Called from main.py lifespan after the app is fully initialised."""
    global _app_state
    _app_state = state

def fetch_weather_task():
    """Fetch real weather data from Open-Meteo and set deterministic traffic."""
    app_logger.info("Scheduler: Executing weather/traffic update task.")
    
    # 1. Fetch Real Weather (Bangalore Coordinates)
    try:
        url = "https://api.open-meteo.com/v1/forecast?latitude=12.9716&longitude=77.5946&current_weather=true"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        weather_code = data.get("current_weather", {}).get("weathercode", 0)
        temp = data.get("current_weather", {}).get("temperature", 25.0)
        
        # Map WMO codes to simple strings
        if weather_code in [0, 1]:
            condition = "Clear"
        elif weather_code in [2, 3]:
            condition = "Cloudy"
        else:
            condition = "Rainy"
            
        weather_str = f"{condition}, {temp}°C"
        app_cache.set('weather', weather_str, ttl_seconds=3600)
        
        # Save to Database
        try:
            if _app_state and hasattr(_app_state, "db_connected") and not _app_state.db_connected:
                app_logger.warning("Skipping DB save for weather (offline mode).")
            else:
                db = SessionLocal()
                # truncate to current hour to prevent duplicates
                current_hour = datetime.datetime.utcnow().replace(minute=0, second=0, microsecond=0)
                existing = db.query(WeatherRecord).filter(WeatherRecord.timestamp == current_hour).first()
                if not existing:
                    precip = data.get("current_weather", {}).get("precipitation", 0.0)
                    db.add(WeatherRecord(
                        timestamp=current_hour,
                        temperature=temp,
                        condition=condition,
                        precipitation=precip
                    ))
                    db.commit()
        except Exception as db_e:
            app_logger.warning(f"Failed to save weather to DB (Database may be offline): {type(db_e).__name__} - {str(db_e)}")
        finally:
            if 'db' in locals():
                db.close()
                
    except requests.exceptions.RequestException as req_e:
        app_logger.warning(f"Weather API unreachable (Network/DNS Error): {type(req_e).__name__} - {str(req_e)}. Using fallback.")
        app_cache.set('weather', "Clear, 28.0°C", ttl_seconds=3600)
    except Exception as e:
        app_logger.error(f"Weather fetch failed unexpectedly: {e}")
        app_cache.set('weather', "Clear, 28.0°C", ttl_seconds=3600)

    # 2. Deterministic Traffic Engine
    hour = datetime.datetime.now().hour
    if 8 <= hour <= 10 or 17 <= hour <= 20:
        traffic = "Heavy"
    elif 11 <= hour <= 16:
        traffic = "Medium"
    else:
        traffic = "Low"
        
    app_cache.set('traffic', traffic, ttl_seconds=3600)

def _run_schedule_engine():
    """Wrapper so APScheduler can call update_schedule_engine with injected deps."""
    try:
        from .services.schedule_engine import update_schedule_engine
        update_schedule_engine(app_state=_app_state, app_cache=app_cache)
    except Exception as e:
        app_logger.error(f"[ScheduleEngine] Batch job failed: {e}")

def _run_demand_aggregation():
    if _app_state and hasattr(_app_state, "db_connected") and not _app_state.db_connected:
        app_logger.warning("[DemandAggregation] Skipping — database is offline.")
        return
        
    from app.database.crud import start_pipeline_execution, finish_pipeline_execution
    try:
        db = SessionLocal()
        run_record = start_pipeline_execution(db, pipeline_name="demand_aggregation")
    except Exception as db_err:
        app_logger.warning(
            f"[DemandAggregation] Skipping — database unavailable: {db_err}"
        )
        return
    try:
        demand_aggregation_service.run_aggregation()
        finish_pipeline_execution(db, execution_id=run_record.id, status="success")
    except Exception as e:
        app_logger.error(f"[DemandAggregation] Job failed: {e}")
        finish_pipeline_execution(db, execution_id=run_record.id, status="failed", error_message=str(e))
    finally:
        db.close()

def _run_continuous_forecasting():
    if _app_state and hasattr(_app_state, "db_connected") and not _app_state.db_connected:
        app_logger.warning("[ContinuousForecasting] Skipping — database is offline.")
        return
        
    try:
        if not _app_state or not getattr(_app_state, "prediction_service", None):
            app_logger.warning("ForecastJob: ML Service not loaded.")
            return

        svc = _app_state.prediction_service
        db = SessionLocal()
        from app.database.crud import start_pipeline_execution, finish_pipeline_execution
        fcst_run = start_pipeline_execution(db, pipeline_name="forecasting")
        opt_run = start_pipeline_execution(db, pipeline_name="optimization")
        try:
            from app.database.models import DemandHistory
            from app.services.demand_prediction_service import demand_prediction_service
            
            target_timestamp = datetime.datetime.utcnow().replace(minute=0, second=0, microsecond=0)
            
            # ── DEBUG LOGGING ──
            app_logger.info(f"DEBUG_FORECAST: target_timestamp={target_timestamp}")
            
            count_all = db.query(DemandHistory).count()
            app_logger.info(f"DEBUG_FORECAST: total_demandhistory_records={count_all}")
            
            latest_record = db.query(DemandHistory).order_by(DemandHistory.timestamp.desc()).first()
            app_logger.info(f"DEBUG_FORECAST: latest_record={latest_record}")
            
            from sqlalchemy import func
            min_max = db.query(func.min(DemandHistory.timestamp), func.max(DemandHistory.timestamp)).first()
            app_logger.info(f"DEBUG_FORECAST: min_timestamp={min_max[0]}, max_timestamp={min_max[1]}")
            
            app_logger.info(f"DEBUG_FORECAST: DemandHistory.__tablename__={DemandHistory.__tablename__}")
            
            # Session connectivity test
            test_records = db.query(DemandHistory).limit(5).all()
            app_logger.info(f"DEBUG_FORECAST: session_connectivity_test_count={len(test_records)}")
            if test_records:
                app_logger.info(f"DEBUG_FORECAST: session_connectivity_test_sample={test_records[0]}")
            
            # ── DEMAND-DRIVEN ROUTE SELECTION ──
            app_logger.info(f"Before collecting demand data: target_timestamp={target_timestamp}")
            recent_demands = db.query(DemandHistory).filter(DemandHistory.timestamp >= target_timestamp - datetime.timedelta(hours=2)).all()
            app_logger.info(f"After DemandHistory query: number of rows returned={len(recent_demands)}")
            
            predictions_added = 0
            route_demands = {}
            route_names = {}
            
            if len(recent_demands) > 0:
                active_routes = {}
                for d in recent_demands:
                    if d.route_id not in active_routes or d.timestamp > active_routes[d.route_id].timestamp:
                        active_routes[d.route_id] = d

                weather = app_cache.get('weather') or 'Clear, 28.0°C'
                traffic = app_cache.get('traffic') or 'Medium'
                hour = datetime.datetime.now().hour
                
                for route_id, d_record in active_routes.items():
                    prediction_result = demand_prediction_service.predict_legacy(
                        route_id=route_id,
                        passenger_count=d_record.passenger_count,
                        occupancy_percent=d_record.occupancy_percent,
                        weather=weather.split(',')[0].strip(),
                        traffic=traffic,
                        hour_of_day=hour
                    )
                    
                    demand = prediction_result.get("route_predicted_passengers", 0)
                    conf = prediction_result.get("confidence", 0.85)
                    version = prediction_result.get("model_source", "catboost+demand_adjusted")
                    
                    create_prediction(
                        db=db,
                        route_id=route_id,
                        predicted_passengers=demand,
                        confidence_score=conf,
                        model_version=version,
                        target_timestamp=target_timestamp
                    )
                    predictions_added += 1
                    route_demands[route_id] = demand
                    route_names[route_id] = route_id
            else:
                app_logger.info("Using ForecastHistory as Fallback Demand Source")
                from app.database.models import ForecastHistory
                latest_forecasts = db.query(ForecastHistory).order_by(ForecastHistory.generated_at.desc()).limit(100).all()
                active_forecasts = {}
                for f in latest_forecasts:
                    if f.route_id not in active_forecasts:
                        active_forecasts[f.route_id] = f
                
                for route_id, f_record in active_forecasts.items():
                    route_demands[route_id] = f_record.route_predicted_passengers or 0
                    route_names[route_id] = route_id
            
            app_logger.info(f"ForecastJob: Generated {predictions_added} predictions.")
            finish_pipeline_execution(db, execution_id=fcst_run.id, status="success")

            # --- OPTIMIZATION SCHEDULER ---
            # Consume real prediction outputs and invoke MILP optimization engine.
            from app.optimization import optimize_fleet
            from app.database.crud import create_optimization_result

            app_logger.info(f"Before optimize_fleet(): route_demands={route_demands}")
            app_logger.info(
                "ForecastJob: Invoking MILP optimization...",
                extra={
                    "extra_data": {
                        "stage": "optimization_start",
                        "routes_count": len(route_demands),
                        "total_demand": sum(route_demands.values()),
                    }
                }
            )
            
            milp_response = optimize_fleet(
                route_demands=route_demands,
                bus_capacity=60,
                max_buses_per_route=10,
                cost_per_bus=1000.0,
                penalty_unmet_demand=50.0,
                alpha=1.0,
                beta=0.7,
                gamma=2.0,
                delta=1.5
            )
            
            if milp_response.get("status") == "error":
                app_logger.error(
                    "MILP optimization failed",
                    extra={
                        "extra_data": {
                            "stage": "optimization_error",
                            "error_details": milp_response.get("error_details"),
                        }
                    }
                )
                finish_pipeline_execution(db, execution_id=opt_run.id, status="failed", error_message=milp_response.get("error_details"))
                return
            
            opt_breakdown = milp_response.get("route_allocation", [])
            summary = milp_response.get("summary", {})

            app_logger.info(
                "SCHED_DIAG | ===== optimize_fleet() RETURNED ===== | "
                "solver_status=%s | routes=%d | total_buses=%d | "
                "total_demand=%d | total_served=%d | total_unmet=%d | efficiency=%.2f%%",
                milp_response.get("status"),
                len(opt_breakdown),
                summary.get("total_buses_used", 0),
                summary.get("total_passengers_demand", 0),
                summary.get("total_passengers_served", 0),
                summary.get("total_unmet_demand", 0),
                summary.get("overall_efficiency_percent", 0.0),
            )
            for alloc in opt_breakdown:
                import math as _math
                app_logger.info(
                    "SCHED_DIAG | alloc | route=%s demand=%d buses_assigned=%s "
                    "required_buses=%d unmet=%d util=%.2f%%",
                    alloc.get("route_id"),
                    alloc.get("demand", 0),
                    alloc.get("buses_assigned"),
                    _math.ceil(alloc.get("demand", 0) / 60) if alloc.get("demand", 0) > 0 else 0,
                    alloc.get("unmet_demand", 0),
                    alloc.get("utilization_percent", 0.0),
                )

            opts_added = 0
            for opt_data in opt_breakdown:
                r_id          = opt_data.get("route_id")
                allocated_buses = int(opt_data.get("buses_assigned") or 0)
                demand          = int(opt_data.get("demand") or 0)
                unmet           = int(opt_data.get("unmet_demand") or 0)
                util            = float(opt_data.get("utilization_percent") or 0.0)

                # Determine priority based on unmet demand
                priority = "MEDIUM"
                if unmet > 10:
                    priority = "HIGH"
                elif unmet == 0 and util > 70:
                    priority = "LOW"

                # Generate recommendation based on MILP results
                if unmet > 0:
                    freq_rec = f"Increase frequency - {unmet} passengers unserved"
                elif util < 50:
                    freq_rec = "Decrease frequency - low utilization"
                else:
                    freq_rec = "Maintain current frequency"

                app_logger.info(
                    "SCHED_DIAG | PRE-INSERT | route=%s allocated_buses=%d (type=%s) "
                    "utilization=%.2f demand=%d unmet=%d priority=%s",
                    r_id, allocated_buses, type(allocated_buses).__name__,
                    util, demand, unmet, priority,
                )

                db_row = create_optimization_result(
                    db=db,
                    route_id=r_id,
                    route_name=route_names.get(r_id, ""),
                    allocated_buses=allocated_buses,
                    utilization=util,
                    objective_score=util,
                    unserved_demand=unmet,
                    priority_level=priority,
                    recommended_frequency=freq_rec,
                    predicted_demand=demand,
                    model_version="catboost+demand_adjusted",
                )

                app_logger.info(
                    "SCHED_DIAG | POST-INSERT verify | row_id=%s route=%s "
                    "stored_allocated_buses=%s stored_utilization=%s "
                    "stored_predicted_demand=%s stored_unserved=%s",
                    getattr(db_row, "id", "?"),
                    getattr(db_row, "route_id", "?"),
                    getattr(db_row, "allocated_buses", "?"),
                    getattr(db_row, "utilization", "?"),
                    getattr(db_row, "predicted_demand", "?"),
                    getattr(db_row, "unserved_demand", "?"),
                )
                opts_added += 1

            app_logger.info(
                "SCHED_DIAG | ===== DB INSERT COMPLETE ===== | rows_inserted=%d | "
                "total_buses_used=%d | total_passengers_served=%d | "
                "overall_efficiency=%.2f%% | total_unmet=%d",
                opts_added,
                summary.get("total_buses_used", 0),
                summary.get("total_passengers_served", 0),
                summary.get("overall_efficiency_percent", 0.0),
                summary.get("total_unmet_demand", 0),
            )

            finish_pipeline_execution(db, execution_id=opt_run.id, status="success")

        except Exception as inner_e:
            finish_pipeline_execution(db, execution_id=fcst_run.id, status="failed", error_message=str(inner_e))
            finish_pipeline_execution(db, execution_id=opt_run.id, status="failed", error_message=str(inner_e))
            raise
        finally:
            # If we exited early without marking success/failure (e.g. uncaught exception),
            # ensure "running" executions are finalized.
            if getattr(fcst_run, "status", None) == "running":
                finish_pipeline_execution(db, execution_id=fcst_run.id, status="failed", error_message="Forecasting terminated unexpectedly")
            if getattr(opt_run, "status", None) == "running":
                finish_pipeline_execution(db, execution_id=opt_run.id, status="failed", error_message="Optimization terminated unexpectedly")
            db.close()
    except Exception as e:
        app_logger.error(f"[ContinuousForecasting] Job failed: {e}")

def start_scheduler():
    if not scheduler.running:
        # ── Job 1: Weather + traffic refresh every 15 min ───────────────────
        scheduler.add_job(
            fetch_weather_task,
            'interval',
            minutes=15,
            id='weather_job',
            replace_existing=True
        )

        # ── Job 2: Demand-based schedule frequency engine every 10 min ──────
        # This is the CITY-LEVEL batch optimiser — not per-request dispatch.
        scheduler.add_job(
            _run_schedule_engine,
            'interval',
            minutes=10,
            id='schedule_engine_job',
            replace_existing=True
        )

        # ── Job 3: Demand Aggregation every 60 mins ──────
        scheduler.add_job(
            _run_demand_aggregation,
            'interval',
            minutes=60,
            id='demand_aggregation_job',
            replace_existing=True
        )

        # ── Job 4: Continuous Forecasting every 60 mins ──────
        scheduler.add_job(
            _run_continuous_forecasting,
            'interval',
            minutes=60,
            id='continuous_forecasting_job',
            replace_existing=True
        )

        # Run all jobs immediately on startup, guarded individually so that
        # a failure in one (e.g. DB unreachable) cannot abort the whole startup.
        try:
            fetch_weather_task()
        except Exception as e:
            app_logger.warning(f"[Scheduler] fetch_weather_task startup run failed (will retry on schedule): {e}")

        try:
            _run_schedule_engine()
        except Exception as e:
            app_logger.warning(f"[Scheduler] _run_schedule_engine startup run failed (will retry on schedule): {e}")

        try:
            _run_demand_aggregation()
        except Exception as e:
            app_logger.warning(f"[Scheduler] _run_demand_aggregation startup run failed (will retry on schedule): {e}")

        try:
            _run_continuous_forecasting()
        except Exception as e:
            app_logger.warning(f"[Scheduler] _run_continuous_forecasting startup run failed (will retry on schedule): {e}")

        scheduler.start()
        app_logger.info("Background Scheduler started (weather + schedule_engine jobs active).")

def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown()
        app_logger.info("Background Scheduler stopped.")
