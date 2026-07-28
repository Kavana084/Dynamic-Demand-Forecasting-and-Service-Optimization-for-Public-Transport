from sqlalchemy.orm import Session
from datetime import datetime
from . import models
from sqlalchemy import func

def get_routes(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Route).offset(skip).limit(limit).all()

def get_predictions(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.ForecastHistory).order_by(models.ForecastHistory.generated_at.desc()).offset(skip).limit(limit).all()

def create_prediction(db: Session, route_id: str, predicted_passengers: int, confidence_score: float, model_version: str, target_timestamp: datetime = None):
    if target_timestamp is None:
        target_timestamp = datetime.utcnow()

    # Canonical forecast history (admin dashboards and insights)
    db_forecast = models.ForecastHistory(
        route_id=route_id,
        predicted_passengers=int(predicted_passengers or 0),
        confidence_score=confidence_score,
        model_version=model_version,
        generated_at=datetime.utcnow(),
        target_timestamp=target_timestamp,
    )
    db.add(db_forecast)

    db.commit()
    db.refresh(db_forecast)
    return db_forecast

def create_optimization_result(db: Session, route_id: str, allocated_buses: int, utilization: float, objective_score: float, unserved_demand: int = 0, priority_level: str = 'MEDIUM', recommended_frequency: str = '', predicted_demand: int = 0, route_name: str = '', model_version: str = 'catboost-v2'):
    db_opt = models.OptimizationResult(
        route_id=route_id,
        route_name=route_name,
        allocated_buses=allocated_buses,
        utilization=utilization,
        objective_score=objective_score,
        unserved_demand=unserved_demand,
        priority_level=priority_level,
        recommended_frequency=recommended_frequency,
        predicted_demand=predicted_demand,
        model_version=model_version,
        timestamp=datetime.utcnow()
    )
    db.add(db_opt)
    db.commit()
    db.refresh(db_opt)
    return db_opt

def get_latest_optimization_result(db: Session, route_id: str):
    return (
        db.query(models.OptimizationResult)
        .filter(models.OptimizationResult.route_id == route_id)
        .order_by(models.OptimizationResult.timestamp.desc())
        .first()
    )

def create_drl_recommendation(db: Session, route_id: str, action: str, confidence: float, expected_reward: float):
    db_drl = models.DRLRecommendation(
        route_id=route_id,
        action=action,
        confidence=confidence,
        expected_reward=expected_reward,
        timestamp=datetime.utcnow()
    )
    db.add(db_drl)
    db.commit()
    db.refresh(db_drl)
    return db_drl

def get_dashboard_summary(db: Session):
    """
    Dashboard summary used by the Overview KPI cards.
    predictedDemand and totalRoutes are scoped to the last 24 hours so the
    Overview section reflects recent activity, not all-time data.
    """
    from datetime import datetime, timedelta
    cutoff_24h = datetime.utcnow() - timedelta(hours=24)

    # Active Routes: distinct routes that have a forecast in the last 24 hours
    total_routes = (
        db.query(func.count(func.distinct(models.ForecastHistory.route_id)))
        .filter(models.ForecastHistory.generated_at >= cutoff_24h)
        .scalar() or 0
    )
    total_stops = db.query(func.count(models.GTFSStop.stop_id)).scalar() or 0

    # TransitObservation is optional; if empty, activeTrips will be 0.
    active_trips = db.query(models.TransitObservation).count()

    # Forecasted Demand: sum of predicted passengers generated in the last 24 hours
    recent_predictions = (
        db.query(models.ForecastHistory)
        .filter(models.ForecastHistory.generated_at >= cutoff_24h)
        .order_by(models.ForecastHistory.generated_at.desc())
        .all()
    )
    predicted_demand = sum(int(p.predicted_passengers or 0) for p in recent_predictions) if recent_predictions else 0

    # Fleet utilization derived from the latest optimization results.
    recent_opts = (
        db.query(models.OptimizationResult)
        .order_by(models.OptimizationResult.timestamp.desc())
        .limit(200)
        .all()
    )
    util_vals = [float(o.utilization) for o in recent_opts if o.utilization is not None]
    fleet_utilization = (sum(util_vals) / len(util_vals)) if util_vals else None

    drl_count = db.query(models.DRLRecommendation).count()
    drl_status = "Active" if drl_count > 0 else "Unavailable"

    return {
        "totalRoutes": total_routes,
        "totalStops": total_stops,
        "activeTrips": active_trips,
        "predictedDemand": predicted_demand,
        "fleetUtilization": fleet_utilization,
        "drlStatus": drl_status,
    }



# ─── Pipeline Execution Logging (Priority 2 Admin remediation) ────────────────

def start_pipeline_execution(
    db: Session,
    pipeline_name: str,
) -> models.PipelineExecutionLog:
    record = models.PipelineExecutionLog(
        pipeline_name=pipeline_name,
        status="running",
        started_at=datetime.utcnow(),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def finish_pipeline_execution(
    db: Session,
    execution_id: int,
    status: str,
    error_message: str | None = None,
) -> models.PipelineExecutionLog | None:
    record = (
        db.query(models.PipelineExecutionLog)
        .filter(models.PipelineExecutionLog.id == execution_id)
        .first()
    )
    if not record:
        return None

    record.status = status
    record.completed_at = datetime.utcnow()
    if record.started_at and record.completed_at:
        record.duration_ms = int((record.completed_at - record.started_at).total_seconds() * 1000)
    record.error_message = error_message
    db.commit()
    db.refresh(record)
    return record


def create_route_plan_log(
    db: Session,
    route_id: str | None,
    source_stop_id: str | None,
    destination_stop_id: str | None,
    route_efficiency: int,
    transfers_count: int | None = None,
    eta_minutes: float | None = None,
    traffic: str | None = None,
    weather: str | None = None,
) -> models.RoutePlanLog:
    record = models.RoutePlanLog(
        route_id=route_id,
        source_stop_id=source_stop_id,
        destination_stop_id=destination_stop_id,
        route_efficiency=int(route_efficiency),
        transfers_count=transfers_count,
        eta_minutes=eta_minutes,
        traffic=traffic,
        weather=weather,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record

def get_hourly_demand_trend(db: Session):
    # Fallback to empty if db is empty
    records = db.query(
        func.extract('hour', models.PredictionRecord.timestamp).label('hour'),
        func.sum(models.PredictionRecord.predicted_passengers).label('passengers')
    ).group_by('hour').order_by('hour').all()
    
    if not records:
        return []
        
    return [{"hour": f"{int(r.hour):02d}:00", "passengers": int(r.passengers)} for r in records]

def get_daily_volume_trend(db: Session):
    # Returns empty array if no historical data is available to prevent fake data
    return [] 

def get_route_popularity(db: Session):
    records = db.query(
        models.ForecastHistory.route_id,
        func.sum(models.ForecastHistory.predicted_passengers).label('demand')
    ).group_by(models.ForecastHistory.route_id).order_by(func.sum(models.ForecastHistory.predicted_passengers).desc()).limit(5).all()
    
    if not records:
        return []
        
    return [{"route": str(r.route_id), "demand": int(r.demand)} for r in records]


# ─── Journey History ──────────────────────────────────────────────────────────

def create_journey_history(
    db: Session,
    user_id: int,
    source_stop_id: str,
    source_stop_name: str,
    destination_stop_id: str,
    destination_stop_name: str,
    route_summary: str,
    transfer_count: int = 0,
    estimated_duration: int = None,
) -> models.JourneyHistory:
    """Insert a journey record whenever a passenger successfully plans a trip."""
    record = models.JourneyHistory(
        user_id=user_id,
        source_stop_id=source_stop_id,
        source_stop_name=source_stop_name,
        destination_stop_id=destination_stop_id,
        destination_stop_name=destination_stop_name,
        route_summary=route_summary,
        transfer_count=transfer_count,
        estimated_duration=estimated_duration,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_journey_history(
    db: Session,
    user_id: int,
    page: int = 1,
    limit: int = 20,
):
    """Return paginated journey history for a user, newest first."""
    offset = (page - 1) * limit
    total = db.query(func.count(models.JourneyHistory.id)).filter(
        models.JourneyHistory.user_id == user_id
    ).scalar()
    items = (
        db.query(models.JourneyHistory)
        .filter(models.JourneyHistory.user_id == user_id)
        .order_by(models.JourneyHistory.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return total, items


# ─── Pipeline Run Tracking ────────────────────────────────────────────────────

def create_pipeline_run(
    db: Session,
    job_type: str,
    status: str = "running",
) -> models.PipelineRun:
    record = models.PipelineRun(
        job_type=job_type,
        status=status,
        started_at=datetime.utcnow()
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record

def update_pipeline_run(
    db: Session,
    run_id: int,
    status: str,
    records_processed: int = 0,
    error_message: str = None
) -> models.PipelineRun:
    record = db.query(models.PipelineRun).filter(models.PipelineRun.id == run_id).first()
    if record:
        record.status = status
        record.completed_at = datetime.utcnow()
        record.records_processed = records_processed
        record.error_message = error_message
        db.commit()
        db.refresh(record)
    return record
