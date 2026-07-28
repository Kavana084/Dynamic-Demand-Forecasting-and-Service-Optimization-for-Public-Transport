import time
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.cache import app_cache
from app.logger import app_logger

# Import services
from app.services.forecast_alignment_service import ForecastAlignmentService
from app.services.analytics_service import AnalyticsService
from app.services.pipeline_monitor_service import PipelineMonitorService
from app.services.data_quality_service import DataQualityService
from app.services.system_monitor_service import SystemMonitorService
from app.services.admin_user_service import AdminUserService
from app.dependencies import verify_admin


# Every route on this router now requires a valid admin/operator credential
# (legacy X-Admin-Token header or a JWT with role Admin/Operator).
router = APIRouter(prefix="/api/admin", dependencies=[Depends(verify_admin)])

ACTIVE_MODEL_VERSION = "catboost+demand_adjusted"

DEFAULT_BUS_CAPACITY = 50  # pax / bus (UI + admin summaries)


def _normalize_scope(value: str | None, all_label: str) -> str | None:
    if value is None:
        return None
    v = str(value).strip()
    if not v or v == all_label:
        return None
    return v


def _parse_dt(v: str | None) -> datetime | None:
    if not v:
        return None
    try:
        return datetime.fromisoformat(v.replace("Z", "+00:00"))
    except Exception:
        try:
            return datetime.strptime(v, "%Y-%m-%d")
        except Exception:
            return None


def _resolve_window(date_from: str | None, date_to: str | None) -> tuple[datetime | None, datetime | None]:
    """
    Operational window for dashboard filtering.

    - Accepts either full ISO timestamps or YYYY-MM-DD dates.
    - `end` is exclusive (safe for BETWEEN-style filters).
    """
    start = _parse_dt(date_from)
    end = _parse_dt(date_to)

    if start and end:
        # if end is a date-only (00:00), treat it as inclusive day by adding 1 day
        if end.hour == 0 and end.minute == 0 and end.second == 0 and end.microsecond == 0:
            end = end + timedelta(days=1)
        elif end <= start:
            end = start + timedelta(days=1)
        return start, end

    if start and not end:
        return start, start + timedelta(days=1)

    if end and not start:
        # treat as "that day"
        if end.hour == 0 and end.minute == 0 and end.second == 0 and end.microsecond == 0:
            start = end
            end = end + timedelta(days=1)
            return start, end
        return end - timedelta(days=1), end

    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    return today - timedelta(days=7), today + timedelta(days=1)


def _apply_route_scope_filter(db: Session, query, route_id_column, region: str | None, depot: str | None):
    """
    Enforce region/depot filters at the database layer (no UI-only filtering).
    """
    region_v = _normalize_scope(region, "All Regions")
    depot_v = _normalize_scope(depot, "All Depots")
    if not region_v and not depot_v:
        return query

    from app.database.models import RouteScope

    route_ids_q = db.query(RouteScope.route_id)
    if region_v:
        route_ids_q = route_ids_q.filter(RouteScope.region == region_v)
    if depot_v:
        route_ids_q = route_ids_q.filter(RouteScope.depot == depot_v)

    return query.filter(route_id_column.in_(route_ids_q.subquery()))


@router.get("/filter-options")
def get_filter_options(
    db: Session = Depends(get_db),
    region: str | None = None,
    depot: str | None = None,
):
    """
    Provides filter dropdown options for region/depot from RouteScope (no hardcoded UI lists).
    """
    from app.database.models import RouteScope

    region_v = _normalize_scope(region, "All Regions")
    depot_v = _normalize_scope(depot, "All Depots")

    q = db.query(RouteScope.region, RouteScope.depot)
    if region_v:
        q = q.filter(RouteScope.region == region_v)
    if depot_v:
        q = q.filter(RouteScope.depot == depot_v)

    rows = q.distinct().all()

    regions = sorted({r for r, _ in rows if r})
    depots = sorted({d for _, d in rows if d})

    return {
        "regions": ["All Regions", *regions],
        "depots": ["All Depots", *depots],
    }


@router.get("/dashboard/insights")
def get_dashboard_insights(
    db: Session = Depends(get_db),
    region: str | None = None,
    depot: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
):
    """
    Backend-generated insights derived from:
      - ForecastHistory (forecast signals + confidence)
      - DemandHistory (actual demand signals)
      - OptimizationResult (allocation/coverage)
      - PipelineExecutionLog + SystemMonitorService (system health)

    No hardcoded confidence values: confidence is computed from model outputs
    (ForecastHistory.confidence_score) or omitted.
    """
    from app.database.models import ForecastHistory, DemandHistory, OptimizationResult, PipelineExecutionLog
    from sqlalchemy import func

    start, end = _resolve_window(date_from, date_to)

    # ── Forecast aggregates ──────────────────────────────────────────────────
    fh_q = db.query(ForecastHistory)
    if start and end:
        fh_q = fh_q.filter(ForecastHistory.target_timestamp >= start, ForecastHistory.target_timestamp < end)
    fh_q = _apply_route_scope_filter(db, fh_q, ForecastHistory.route_id, region, depot)

    total_forecast = fh_q.with_entities(func.sum(ForecastHistory.predicted_passengers)).scalar()
    avg_conf = fh_q.with_entities(func.avg(ForecastHistory.confidence_score)).scalar()

    # Compute change vs previous window (same duration) when a window is provided.
    forecast_change_pct = None
    if start and end:
        duration = end - start
        prev_start = start - duration
        prev_end = start
        prev_q = db.query(ForecastHistory).filter(
            ForecastHistory.target_timestamp >= prev_start,
            ForecastHistory.target_timestamp < prev_end,
        )
        prev_q = _apply_route_scope_filter(db, prev_q, ForecastHistory.route_id, region, depot)
        prev_total = prev_q.with_entities(func.sum(ForecastHistory.predicted_passengers)).scalar()
        if prev_total and float(prev_total) > 0:
            forecast_change_pct = ((float(total_forecast or 0) - float(prev_total)) / float(prev_total)) * 100.0

    insights = []

    if forecast_change_pct is not None and avg_conf is not None:
        # Only surface meaningful deltas to keep the panel readable.
        if abs(forecast_change_pct) >= 10:
            direction = "increase" if forecast_change_pct > 0 else "decrease"
            insights.append({
                "recommendation": f"Passenger demand is forecasted to {direction} by {abs(forecast_change_pct):.0f}% for the selected window.",
                "confidence": float(avg_conf),
                "explainability": "Computed as percent change in total forecasted passengers (ForecastHistory) vs the immediately preceding window of equal duration.",
                "actions": [{"label": "Review forecasting", "to": "/admin/analytics", "tab": "forecasting"}],
            })

    # ── Capacity risk (Forecast vs allocated capacity) ───────────────────────
    # Pick latest optimization per route in the window (or overall if no window).
    from app.database.models import Route
    opt_q = db.query(OptimizationResult).join(Route, OptimizationResult.route_id == Route.route_id)
    if start and end:
        opt_q = opt_q.filter(OptimizationResult.timestamp >= start, OptimizationResult.timestamp < end)
    opt_q = _apply_route_scope_filter(db, opt_q, OptimizationResult.route_id, region, depot)
    latest_opt_rows = (
        opt_q.order_by(OptimizationResult.timestamp.desc())
        .limit(500)
        .all()
    )
    opt_by_route = {}
    for r in latest_opt_rows:
        if r.route_id not in opt_by_route:
            opt_by_route[r.route_id] = r

    # Find peak forecast per route in window.
    peak_by_route = (
        fh_q.with_entities(
            ForecastHistory.route_id.label("route_id"),
            func.max(ForecastHistory.predicted_passengers).label("peak_pred"),
            func.avg(ForecastHistory.confidence_score).label("route_conf"),
        )
        .group_by(ForecastHistory.route_id)
        .all()
    )

    risks = []
    for row in peak_by_route:
        opt = opt_by_route.get(row.route_id)
        if not opt:
            continue
        allocated = _safe_int(getattr(opt, "allocated_buses", 0), 0)
        cap = allocated * DEFAULT_BUS_CAPACITY
        peak_pred = _safe_int(row.peak_pred, 0)
        if allocated <= 0:
            continue
        if peak_pred > cap:
            opt = opt_by_route.get(row.route_id)
            route_short_name = opt.route.route_short_name or opt.route.route_long_name or opt.route.name or row.route_id if opt else row.route_id
            risks.append({
                "route_id": row.route_id,
                "route_short_name": route_short_name,
                "peak_pred": peak_pred,
                "capacity": cap,
                "gap_pax": peak_pred - cap,
                "confidence": float(row.route_conf) if row.route_conf is not None else None,
            })

    risks.sort(key=lambda r: r["gap_pax"], reverse=True)
    for r in risks[:3]:
        insights.append({
            "recommendation": f"Route {r['route_short_name']} may exceed allocated capacity during the selected window.",
            "confidence": r["confidence"],
            "explainability": f"Peak forecasted demand ({r['peak_pred']}) exceeds allocated capacity ({r['capacity']}) assuming {DEFAULT_BUS_CAPACITY} passengers per bus.",
            "actions": [{"label": "Open route comparison", "to": "/admin/analytics", "tab": "comparisons", "route": r["route_id"]}],
        })

    # ── Pipeline reliability insight (failures in last 7 days) ───────────────
    lookback = datetime.utcnow() - timedelta(days=7)
    failures = (
        db.query(func.count(PipelineExecutionLog.id))
        .filter(PipelineExecutionLog.status == "failed", PipelineExecutionLog.started_at >= lookback)
        .scalar()
        or 0
    )
    if failures > 0:
        insights.append({
            "recommendation": f"{failures} pipeline run(s) failed in the last 7 days. Review pipeline logs and rerun failed stages.",
            "confidence": None,
            "explainability": "Derived from PipelineExecutionLog status=failed within the last 7 days.",
            "actions": [{"label": "Open monitoring", "to": "/admin/system", "tab": "pipelines"}],
        })

    return insights[:4]


def _timed(label, fn):
    started = time.perf_counter()
    value = fn()
    return label, value, round((time.perf_counter() - started) * 1000, 2)


def _fallback_payload(message: str, details: str | None = None):
    payload = {
        "available": False,
        "message": message,
    }
    if details:
        payload["details"] = details
    return payload

def _safe_int(value, default=0):
    try:
        n = int(value)
        return n
    except Exception:
        return default

def _required_buses(predicted_demand: int, capacity: int = DEFAULT_BUS_CAPACITY) -> int:
    d = _safe_int(predicted_demand, 0)
    if d <= 0:
        return 0
    cap = max(1, int(capacity))
    # ceiling division
    return (d + cap - 1) // cap

def _utilization(predicted_demand: int, allocated_buses: int, capacity: int = DEFAULT_BUS_CAPACITY) -> float:
    """
    Business utilization: demand / capacity_provided, normalized 0..1.
    This avoids placeholder values like 9170% that break dashboards.
    """
    d = float(_safe_int(predicted_demand, 0))
    a = float(_safe_int(allocated_buses, 0))
    if a <= 0:
        return 0.0
    denom = max(1.0, a * float(max(1, capacity)))
    return max(0.0, min(1.0, d / denom))

# 1. AI Performance & Forecast Alignment
@router.get("/ai/performance")
def get_ai_performance(db: Session = Depends(get_db)):
    try:
        report = ForecastAlignmentService.get_alignment_report(db)
        report["available"] = True
        return report
    except Exception as exc:
        app_logger.exception(
            "AI performance metrics unavailable",
            extra={
                "extra_data": {
                    "endpoint": "/api/admin/ai/performance",
                    "error_message": str(exc),
                }
            },
        )
        return _fallback_payload(
            "AI metrics temporarily unavailable",
            "Forecast alignment query failed; dashboard widgets can continue with fallback state.",
        )

# 2. Analytics Dashboard
@router.get("/analytics/demand")
def get_analytics_demand(
    db: Session = Depends(get_db),
    region: str | None = None,
    depot: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
):
    start, end = _resolve_window(date_from, date_to)

    summary = AnalyticsService.get_dashboard_summary(db, start=start, end=end, region=region, depot=depot)
    return {
        "summary": summary
    }

@router.get("/analytics/demand-distribution")
def get_analytics_demand_distribution(
    db: Session = Depends(get_db),
    region: str | None = None,
    depot: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
):
    start, end = _resolve_window(date_from, date_to)

    distribution = AnalyticsService.get_demand_distribution(db, start=start, end=end, region=region, depot=depot)
    return distribution

@router.get("/analytics/peak-hour")
def get_analytics_peak_hour(
    db: Session = Depends(get_db),
    region: str | None = None,
    depot: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
):
    start, end = _resolve_window(date_from, date_to)

    peak_hours = AnalyticsService.get_peak_hour_analysis(db, start=start, end=end, region=region, depot=depot)
    return peak_hours

@router.get("/analytics/route-ranking")
def get_analytics_route_ranking(
    db: Session = Depends(get_db),
    region: str | None = None,
    depot: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
):
    start, end = _resolve_window(date_from, date_to)

    ranking = AnalyticsService.get_route_ranking(db, start=start, end=end, region=region, depot=depot)
    return ranking


@router.get("/analytics/demand-heatmap")
def get_demand_heatmap(
    db: Session = Depends(get_db),
    region: str | None = None,
    depot: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
):
    """
    Backend-generated demand heatmap (no synthetic/frontend-computed matrix).
    """
    start, end = _resolve_window(date_from, date_to)
    return AnalyticsService.get_demand_heatmap(db, start=start, end=end, region=region, depot=depot)

# 3. Pipeline Monitor
@router.get("/pipeline/monitor")
def get_pipeline_monitor(db: Session = Depends(get_db)):
    return PipelineMonitorService.get_pipeline_status(db)

@router.get("/pipeline/validation")
def get_pipeline_validation(db: Session = Depends(get_db)):
    from app.database.models import JourneyHistory, DemandHistory, ForecastHistory, OptimizationResult
    
    journey_count = db.query(JourneyHistory).count()
    demand_count = db.query(DemandHistory).count()
    prediction_count = db.query(ForecastHistory).count()
    opt_count = db.query(OptimizationResult).count()
    demand_prediction_count = db.query(ForecastHistory).filter(ForecastHistory.model_version == ACTIVE_MODEL_VERSION).count()
    demand_opt_count = db.query(OptimizationResult).filter(OptimizationResult.model_version == ACTIVE_MODEL_VERSION).count()
    legacy_prediction_count = prediction_count - demand_prediction_count
    legacy_opt_count = opt_count - demand_opt_count
    
    status = "healthy"
    if demand_count == 0 or demand_prediction_count == 0 or demand_opt_count == 0:
        status = "degraded"
        
    return {
        "status": status,
        "journey_history_count": journey_count,
        "demand_history_count": demand_count,
        "prediction_records_count": prediction_count,
        "optimization_results_count": opt_count,
        "journey_history": journey_count,
        "demand_history": demand_count,
        "prediction_records": {
            "legacy": legacy_prediction_count,
            "demand_driven": demand_prediction_count,
        },
        "optimization_results": {
            "legacy": legacy_opt_count,
            "demand_driven": demand_opt_count,
        },
    }

# 4. Data Quality
@router.get("/data-quality")
def get_data_quality(db: Session = Depends(get_db)):
    return DataQualityService.get_data_quality(db)

# 5. System Monitoring
@router.get("/system/health")
def get_system_health(db: Session = Depends(get_db)):
    return SystemMonitorService.get_system_health(db)


@router.get("/dashboard/bootstrap")
def get_dashboard_bootstrap(
    db: Session = Depends(get_db),
    region: str | None = None,
    depot: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
):
    # Filter-aware cache key (prevents UI-only filters / cross-scope leakage)
    region_v = _normalize_scope(region, "All Regions") or "all"
    depot_v = _normalize_scope(depot, "All Depots") or "all"
    cache_key = f"admin_dashboard_bootstrap:v2:{region_v}:{depot_v}:{date_from or ''}:{date_to or ''}"
    cached = app_cache.get(cache_key)
    if cached is not None:
        payload = dict(cached)
        payload["cached"] = True
        return payload

    timings = {}
    errors = {}
    payload = {}

    # NOTE: Only include sections that are actually rendered by AdminDashboard.jsx.
    # demand_trend, fleet_utilization, recent_demand, latest_predictions, and
    # recent_optimizations are excluded here — they are available via their own
    # direct endpoints for pages that need them (AnalyticsDashboard, OptimizationInsights).
    jobs = [
        ("kpis",            lambda: get_overview_kpis(db, region=region, depot=depot, date_from=date_from, date_to=date_to)),
        ("insights",        lambda: get_dashboard_insights(db, region=region, depot=depot, date_from=date_from, date_to=date_to)),
        ("filter_options",  lambda: get_filter_options(db, region=region, depot=depot)),
        ("data_quality",    lambda: get_data_quality(db)),
        ("system_health",   lambda: get_system_health(db)),
        ("pipeline_monitor",lambda: get_pipeline_monitor(db)),
    ]

    for key, fn in jobs:
        try:
            label, value, elapsed = _timed(key, fn)
            payload[label] = value
            timings[label] = elapsed
        except Exception as exc:
            app_logger.exception(
                "Dashboard bootstrap section failed",
                extra={
                    "extra_data": {
                        "endpoint": "/api/admin/dashboard/bootstrap",
                        "section": key,
                        "error_message": str(exc),
                    }
                },
            )
            errors[key] = str(exc)
            payload[key] = None

    result = {
        "available": True,
        "cached": False,
        "sections": payload,
        "errors": errors,
        "timings_ms": timings,
    }
    app_cache.set(cache_key, result, ttl_seconds=30)
    return result

# 6. Optimization Insights & Explainability
@router.get("/optimization/insights")
def get_optimization_insights(db: Session = Depends(get_db)):
    from app.database.models import OptimizationResult, ForecastHistory, Route
    from sqlalchemy import func

    # Just a simple aggregation for insights
    latest = (
        db.query(OptimizationResult).join(Route, OptimizationResult.route_id == Route.route_id)
        .filter(OptimizationResult.model_version == ACTIVE_MODEL_VERSION)
        .order_by(OptimizationResult.timestamp.desc())
        .limit(250)
        .all()
    )

    # Fallback: if envs still write older model_version values, show something rather than blank.
    if not latest:
        latest = db.query(OptimizationResult).join(Route, OptimizationResult.route_id == Route.route_id).order_by(OptimizationResult.timestamp.desc()).limit(250).all()

    total_allocated = sum(_safe_int(r.allocated_buses, 0) for r in latest)
    total_required = sum(_required_buses(r.predicted_demand) for r in latest)
    fleet_gap = total_required - total_allocated

    util_vals = [_utilization(r.predicted_demand, r.allocated_buses) for r in latest]
    avg_util = (sum(util_vals) / len(util_vals)) if util_vals else None

    # Most recent allocations table (UI-ready fields)
    allocations = sorted(latest, key=lambda r: r.timestamp or 0, reverse=True)[:15]

    # Simple explainable recommendations: highlight top shortages and surpluses
    scored = []
    for r in latest:
        required = _required_buses(r.predicted_demand)
        allocated = _safe_int(r.allocated_buses, 0)
        gap = required - allocated
        scored.append((gap, r))

    top_short = [it for it in scored if it[0] > 0][:5]
    top_short.sort(key=lambda t: t[0], reverse=True)

    # Confidence is derived from ForecastHistory model outputs (no hardcoded values).
    short_route_ids = [r.route_id for _, r in top_short[:3] if getattr(r, "route_id", None)]
    conf_by_route = {}
    if short_route_ids:
        rows = (
            db.query(
                ForecastHistory.route_id,
                func.avg(ForecastHistory.confidence_score).label("avg_conf"),
            )
            .filter(ForecastHistory.route_id.in_(short_route_ids))
            .group_by(ForecastHistory.route_id)
            .all()
        )
        conf_by_route = {rid: (float(avg) if avg is not None else None) for rid, avg in rows}

    recommendations = []
    for gap, r in top_short[:3]:
        route_short_name = r.route.route_short_name or r.route_long_name or r.name or r.route_id
        recommendations.append({
            "route_id": r.route_id,
            "route_short_name": route_short_name,
            "action": f"Add {gap} bus{'es' if gap != 1 else ''} to Route {route_short_name}",
            "confidence": conf_by_route.get(r.route_id),
            "reason": f"Predicted demand requires {gap} more bus{'es' if gap != 1 else ''} assuming {DEFAULT_BUS_CAPACITY} pax/bus.",
        })

    explain = (
        "Required buses are derived from predicted passenger demand divided by an assumed bus capacity. "
        "Utilization is normalized as demand / provided capacity and clamped to 0–100%."
    )

    return {
        "fleet_summary": {
            "allocated_buses": total_allocated,
            "required_buses": total_required,
            "fleet_gap": fleet_gap,
            "utilization": avg_util,
            "assumed_bus_capacity": DEFAULT_BUS_CAPACITY,
        },
        "recent_allocations": [
            {
                "route_id": a.route_id,
                "route_short_name": a.route.route_short_name or a.route_long_name or a.name or a.route_id,
                "route_name": a.route_name or a.route_id,
                "allocated": _safe_int(a.allocated_buses, 0),
                "predicted_demand": _safe_int(a.predicted_demand, 0),
                "utilization": _utilization(a.predicted_demand, a.allocated_buses),
                "timestamp": a.timestamp,
            } for a in allocations
        ],
        "recommendations": recommendations,
        "explainability": explain,
    }

# 7. User Access Management
@router.get("/users")
def get_users(db: Session = Depends(get_db)):
    return AdminUserService.get_all_users(db)

from pydantic import BaseModel
from fastapi import Request

class CreateUserReq(BaseModel):
    username: str
    role: str

@router.post("/users")
def create_user(req: CreateUserReq, request: Request, db: Session = Depends(get_db), admin: dict = Depends(verify_admin)):
    admin_username = admin.get("username", "admin")
    ip_address = request.client.host if request.client else "Unknown"
    return AdminUserService.create_user(db, admin_username, req.username, req.role, ip_address)

class ToggleUserReq(BaseModel):
    is_active: bool

@router.put("/users/{user_id}/toggle")
def toggle_user(user_id: int, req: ToggleUserReq, request: Request, db: Session = Depends(get_db), admin: dict = Depends(verify_admin)):
    admin_username = admin.get("username", "admin")
    ip_address = request.client.host if request.client else "Unknown"
    return AdminUserService.toggle_user_status(db, admin_username, user_id, req.is_active, ip_address)

class RoleChangeReq(BaseModel):
    role: str

@router.put("/users/{user_id}/role")
def change_role(user_id: int, req: RoleChangeReq, request: Request, db: Session = Depends(get_db), admin: dict = Depends(verify_admin)):
    admin_username = admin.get("username", "admin")
    ip_address = request.client.host if request.client else "Unknown"
    return AdminUserService.change_role(db, admin_username, user_id, req.role, ip_address)

@router.post("/users/{user_id}/reset-password")
def reset_password(user_id: int, request: Request, db: Session = Depends(get_db), admin: dict = Depends(verify_admin)):
    # Backward-compat route (deprecated): keep endpoint but do NOT return passwords.
    admin_username = admin.get("username", "admin")
    ip_address = request.client.host if request.client else "Unknown"
    return AdminUserService.send_reset_link(db, admin_username, user_id, ip_address)

@router.post("/users/{user_id}/send-reset-link")
def send_reset_link(user_id: int, request: Request, db: Session = Depends(get_db), admin: dict = Depends(verify_admin)):
    admin_username = admin.get("username", "admin")
    ip_address = request.client.host if request.client else "Unknown"
    return AdminUserService.send_reset_link(db, admin_username, user_id, ip_address)

class ScopeReq(BaseModel):
    region: str | None = None
    depot: str | None = None

@router.put("/users/{user_id}/scope")
def update_user_scope(user_id: int, req: ScopeReq, request: Request, db: Session = Depends(get_db), admin: dict = Depends(verify_admin)):
    admin_username = admin.get("username", "admin")
    ip_address = request.client.host if request.client else "Unknown"
    return AdminUserService.set_scope(db, admin_username, user_id, req.region, req.depot, ip_address)

class MfaReq(BaseModel):
    mfa_enabled: bool

@router.put("/users/{user_id}/mfa")
def update_user_mfa(user_id: int, req: MfaReq, request: Request, db: Session = Depends(get_db), admin: dict = Depends(verify_admin)):
    admin_username = admin.get("username", "admin")
    ip_address = request.client.host if request.client else "Unknown"
    return AdminUserService.set_mfa(db, admin_username, user_id, req.mfa_enabled, ip_address)

class LockReq(BaseModel):
    is_locked: bool

@router.put("/users/{user_id}/lock")
def update_user_lock(user_id: int, req: LockReq, request: Request, db: Session = Depends(get_db), admin: dict = Depends(verify_admin)):
    admin_username = admin.get("username", "admin")
    ip_address = request.client.host if request.client else "Unknown"
    return AdminUserService.set_lock(db, admin_username, user_id, req.is_locked, ip_address)

@router.delete("/users/{user_id}")
def soft_delete_user(user_id: int, request: Request, db: Session = Depends(get_db), admin: dict = Depends(verify_admin)):
    admin_username = admin.get("username", "admin")
    ip_address = request.client.host if request.client else "Unknown"
    return AdminUserService.soft_delete_user(db, admin_username, user_id, ip_address)

# 8. Audit Logs
@router.get("/audit-logs")
def get_audit_logs(
    db: Session = Depends(get_db),
    q: str = None,
    user: str = None,
    module: str = None,
    status: str = None,
    date_from: str = None,
    date_to: str = None,
    limit: int = 500,
):
    from datetime import datetime

    def _parse_dt(v: str):
        if not v:
            return None
        # Accept either full ISO or YYYY-MM-DD
        try:
            return datetime.fromisoformat(v.replace("Z", "+00:00"))
        except Exception:
            try:
                return datetime.strptime(v, "%Y-%m-%d")
            except Exception:
                return None

    logs = AdminUserService.get_audit_logs(
        db,
        q=q,
        user=user,
        module=module,
        status=status,
        date_from=_parse_dt(date_from),
        date_to=_parse_dt(date_to),
        limit=limit,
    )
    return [
        {
            "id": l.id,
            # UI-facing core columns
            "timestamp": l.timestamp,
            "user": l.admin_username,
            "action": l.action,
            "module": getattr(l, "module", None) or "User Administration",
            "status": getattr(l, "status", None) or "success",

            # Detail drawer fields
            "target_user": l.target_user,
            "detail": getattr(l, "detail", None),
            "previous_value": l.previous_value,
            "new_value": l.new_value,
            "ip_address": l.ip_address,
        } for l in logs
    ]

# 9. Historical Monitoring
@router.get("/historical/monitoring")
def get_historical_monitoring(db: Session = Depends(get_db)):
    # Retrieve recent model metadata for RMSE trend
    from app.database.models import ModelMetadata, ForecastHistory, OptimizationResult
    from sqlalchemy import func
    
    meta = db.query(ModelMetadata).order_by(ModelMetadata.trained_at.desc()).limit(10).all()
    rmse_trend = [{"timestamp": m.trained_at, "rmse": m.rmse} for m in reversed(meta)]
    
    # Very basic prediction volume trend
    preds = db.query(
        func.date(ForecastHistory.generated_at).label("date"), 
        func.count(ForecastHistory.id).label("count")
    ).group_by("date").order_by("date").limit(7).all()
    pred_vol = [{"date": str(p.date), "count": p.count} for p in preds]
    
    opts = db.query(
        func.date(OptimizationResult.timestamp).label("date"), 
        func.count(OptimizationResult.id).label("count")
    ).group_by("date").order_by("date").limit(7).all()
    opt_runs = [{"date": str(o.date), "count": o.count} for o in opts]
    
    return {
        "forecastAccuracyTrend": [], # To be fully populated with actual aligned accuracy in analytics if needed
        "rmseTrend": rmse_trend,
        "predictionVolumeTrend": pred_vol,
        "optimizationRunTrend": opt_runs
    }

# 10. Overview Dashboard KPIs
@router.get("/overview-kpis")
def get_overview_kpis(
    db: Session = Depends(get_db),
    region: str | None = None,
    depot: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
):
    """
    All KPIs are computed from database queries and/or model outputs:
      - passengers: sum(DemandHistory.passenger_count)
      - forecasted_demand: sum(ForecastHistory.predicted_passengers)
      - utilization: derived from OptimizationResult via _utilization()
    """
    from app.database.models import DemandHistory, ForecastHistory, OptimizationResult, RoutePlanLog
    from sqlalchemy import func

    start, end = _resolve_window(date_from, date_to)
    if not start or not end:
        # Default to "today" (UTC) if no window is provided.
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        start, end = today, today + timedelta(days=1)

    app_logger.info(
        "Dashboard KPI query window",
        extra={
            "extra_data": {
                "endpoint": "/api/admin/overview-kpis",
                "date_from": date_from,
                "date_to": date_to,
                "resolved_start": start.isoformat(),
                "resolved_end": end.isoformat(),
                "region": region,
                "depot": depot,
            }
        }
    )

    prev_start = start - (end - start)
    prev_end = start

    def _pct_change(current: float | int | None, prev: float | int | None) -> float | None:
        if prev is None:
            return None
        try:
            prev_v = float(prev)
            if prev_v == 0:
                return None
            return ((float(current or 0) - prev_v) / prev_v) * 100.0
        except Exception:
            return None

    # Passengers (actual demand)
    dh_q = db.query(DemandHistory).filter(DemandHistory.timestamp >= start, DemandHistory.timestamp < end)
    dh_q = _apply_route_scope_filter(db, dh_q, DemandHistory.route_id, region, depot)
    total_passengers = dh_q.with_entities(func.sum(DemandHistory.passenger_count)).scalar()

    dh_prev_q = db.query(DemandHistory).filter(DemandHistory.timestamp >= prev_start, DemandHistory.timestamp < prev_end)
    dh_prev_q = _apply_route_scope_filter(db, dh_prev_q, DemandHistory.route_id, region, depot)
    prev_passengers = dh_prev_q.with_entities(func.sum(DemandHistory.passenger_count)).scalar()

    # Helper to get the latest records per route for a given model class and timestamp field
    def _get_latest_per_route(model_class, time_field, window_start=None, window_end=None):
        subq = db.query(
            model_class.route_id,
            func.max(time_field).label('max_time')
        )
        if window_start is not None:
            subq = subq.filter(time_field >= window_start)
        if window_end is not None:
            subq = subq.filter(time_field < window_end)
        subq = subq.group_by(model_class.route_id).subquery()
        
        q = db.query(model_class).join(
            subq,
            (model_class.route_id == subq.c.route_id) &
            (time_field == subq.c.max_time)
        )
        return _apply_route_scope_filter(db, q, model_class.route_id, region, depot)

    fh_latest_q = _get_latest_per_route(ForecastHistory, ForecastHistory.generated_at, window_end=end)
    fh_prev_latest_q = _get_latest_per_route(ForecastHistory, ForecastHistory.generated_at, window_end=start)

    # Total routes (count all routes from Route table - no scope filter for total count)
    from app.database.models import Route
    total_routes = db.query(Route).with_entities(func.count(func.distinct(Route.route_id))).scalar() or 0

    # Active routes (sourced directly from OptimizationResult to match optimization engine output)
    opt_active_q = db.query(OptimizationResult).filter(OptimizationResult.timestamp >= start, OptimizationResult.timestamp < end)
    opt_active_q = _apply_route_scope_filter(db, opt_active_q, OptimizationResult.route_id, region, depot)
    active_routes = opt_active_q.with_entities(func.count(func.distinct(OptimizationResult.route_id))).scalar() or 0
    if active_routes == 0:
        # Fallback: if no optimization results in the current window, use the total distinct optimized routes
        active_routes_fallback_q = _apply_route_scope_filter(db, db.query(OptimizationResult), OptimizationResult.route_id, region, depot)
        active_routes = active_routes_fallback_q.with_entities(func.count(func.distinct(OptimizationResult.route_id))).scalar() or 0

    opt_prev_q = db.query(OptimizationResult).filter(OptimizationResult.timestamp >= prev_start, OptimizationResult.timestamp < prev_end)
    opt_prev_q = _apply_route_scope_filter(db, opt_prev_q, OptimizationResult.route_id, region, depot)
    prev_active_routes = opt_prev_q.with_entities(func.count(func.distinct(OptimizationResult.route_id))).scalar() or 0

    # Forecasted demand (model output) - aggregate ALL forecasts within the time window
    fh_q = db.query(ForecastHistory).filter(ForecastHistory.generated_at >= start, ForecastHistory.generated_at < end)
    fh_q = _apply_route_scope_filter(db, fh_q, ForecastHistory.route_id, region, depot)
    forecasted_demand = fh_q.with_entities(func.sum(ForecastHistory.predicted_passengers)).scalar()
    
    # Previous window forecasted demand
    fh_prev_q = db.query(ForecastHistory).filter(ForecastHistory.generated_at >= prev_start, ForecastHistory.generated_at < prev_end)
    fh_prev_q = _apply_route_scope_filter(db, fh_prev_q, ForecastHistory.route_id, region, depot)
    prev_forecasted_demand = fh_prev_q.with_entities(func.sum(ForecastHistory.predicted_passengers)).scalar()

    # Allocated buses + utilization (optimization output) - sum ALL allocations in last 24 hours
    # Use 24-hour window regardless of selected date range for this metric
    now_24h_ago = datetime.utcnow() - timedelta(hours=24)
    opt_24h_q = db.query(OptimizationResult).filter(OptimizationResult.timestamp >= now_24h_ago)
    opt_24h_q = _apply_route_scope_filter(db, opt_24h_q, OptimizationResult.route_id, region, depot)
    allocated_buses = opt_24h_q.with_entities(func.sum(OptimizationResult.allocated_buses)).scalar()

    recent_opts = opt_24h_q.all()
    # Use MILP-calculated utilization directly from OptimizationResult instead of recalculating
    util_vals = [float(o.utilization) for o in recent_opts if o.utilization is not None]
    avg_utilization = (sum(util_vals) / len(util_vals)) if util_vals else None

    # Route efficiency KPI (computed from actual routing outcomes)
    rp_q = db.query(RoutePlanLog).filter(RoutePlanLog.created_at >= start, RoutePlanLog.created_at < end)
    rp_q = _apply_route_scope_filter(db, rp_q, RoutePlanLog.route_id, region, depot)
    avg_route_efficiency = rp_q.with_entities(func.avg(RoutePlanLog.route_efficiency)).scalar()

    rp_prev_q = db.query(RoutePlanLog).filter(RoutePlanLog.created_at >= prev_start, RoutePlanLog.created_at < prev_end)
    rp_prev_q = _apply_route_scope_filter(db, rp_prev_q, RoutePlanLog.route_id, region, depot)
    prev_route_eff = rp_prev_q.with_entities(func.avg(RoutePlanLog.route_efficiency)).scalar()

    return {
        "window": {"start": start.isoformat(), "end": end.isoformat()},
        "total_passengers": int(total_passengers or 0),
        "total_passengers_change": (round(_pct_change(total_passengers, prev_passengers), 1) if _pct_change(total_passengers, prev_passengers) is not None else None),
        "total_routes": int(total_routes or 0),
        "active_routes": int(active_routes or 0),
        "active_routes_change": (round(_pct_change(active_routes, prev_active_routes), 1) if _pct_change(active_routes, prev_active_routes) is not None else None),
        "forecasted_demand": int(forecasted_demand) if forecasted_demand is not None else None,
        "forecasted_demand_change": (round(_pct_change(forecasted_demand, prev_forecasted_demand), 1) if _pct_change(forecasted_demand, prev_forecasted_demand) is not None else None),
        "allocated_buses": int(allocated_buses) if allocated_buses is not None else None,
        "avg_utilization": float(avg_utilization) if avg_utilization is not None else None,
        "avg_route_efficiency": float(avg_route_efficiency) if avg_route_efficiency is not None else None,
        "avg_route_efficiency_change": (round(_pct_change(avg_route_efficiency, prev_route_eff), 1) if _pct_change(avg_route_efficiency, prev_route_eff) is not None else None),
        "assumed_bus_capacity": DEFAULT_BUS_CAPACITY,
        "message": None,
    }

# 11. Overview Dashboard Tables & Charts Data
@router.get("/tables/recent-demand")
def get_recent_demand_table(
    db: Session = Depends(get_db),
    region: str | None = None,
    depot: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
):
    from app.database.models import DemandHistory
    start, end = _resolve_window(date_from, date_to)
    q = db.query(DemandHistory)
    if start and end:
        q = q.filter(DemandHistory.timestamp >= start, DemandHistory.timestamp < end)
    q = _apply_route_scope_filter(db, q, DemandHistory.route_id, region, depot)
    records = q.order_by(DemandHistory.timestamp.desc()).limit(10).all()
    return [
        {
            "route_id": r.route_id,
            "passenger_count": r.passenger_count,
            "occupancy_percent": r.occupancy_percent,
            "timestamp": r.timestamp.isoformat()
        } for r in records
    ]

@router.get("/tables/latest-predictions")
def get_latest_predictions_table(
    db: Session = Depends(get_db),
    region: str | None = None,
    depot: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
):
    from app.database.models import ForecastHistory, Route
    start, end = _resolve_window(date_from, date_to)
    q = db.query(ForecastHistory).join(Route, ForecastHistory.route_id == Route.route_id)
    if start and end:
        q = q.filter(ForecastHistory.target_timestamp >= start, ForecastHistory.target_timestamp < end)
    q = _apply_route_scope_filter(db, q, ForecastHistory.route_id, region, depot)
    records = q.order_by(ForecastHistory.target_timestamp.desc()).limit(10).all()
    return [
        {
            "route_id": r.route_id,
            "route_short_name": r.route.route_short_name or r.route_long_name or r.name or r.route_id,
            "predicted_demand": r.predicted_passengers,
            "confidence": r.confidence_score,
            "model_version": r.model_version,
            "time": r.target_timestamp.isoformat() if r.target_timestamp else r.generated_at.isoformat()
        } for r in records
    ]

@router.get("/tables/recent-optimizations")
def get_recent_optimizations_table(
    db: Session = Depends(get_db),
    region: str | None = None,
    depot: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
):
    from app.database.models import OptimizationResult, Route
    start, end = _resolve_window(date_from, date_to)
    q = db.query(OptimizationResult).join(Route, OptimizationResult.route_id == Route.route_id)
    if start and end:
        q = q.filter(OptimizationResult.timestamp >= start, OptimizationResult.timestamp < end)
    q = _apply_route_scope_filter(db, q, OptimizationResult.route_id, region, depot)
    records = q.order_by(OptimizationResult.timestamp.desc()).limit(10).all()
    return [
        {
            "route_id": r.route_id,
            "route_short_name": r.route.route_short_name or r.route_long_name or r.name or r.route_id,
            "route_name": r.route_name or r.route_id,
            "allocated_buses": r.allocated_buses,
            "utilization": _utilization(r.predicted_demand, r.allocated_buses),
            "model_version": r.model_version,
            "time": r.timestamp.isoformat()
        } for r in records
    ]

@router.get("/charts/demand-trend")
def get_demand_trend_chart(
    db: Session = Depends(get_db),
    region: str | None = None,
    depot: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
):
    from app.database.models import ForecastHistory, Route
    start, end = _resolve_window(date_from, date_to)
    q = db.query(ForecastHistory).join(Route, ForecastHistory.route_id == Route.route_id)
    if start and end:
        q = q.filter(ForecastHistory.target_timestamp >= start, ForecastHistory.target_timestamp < end)
    q = _apply_route_scope_filter(db, q, ForecastHistory.route_id, region, depot)
    records = q.order_by(ForecastHistory.target_timestamp.asc()).limit(100).all()
    return [
        {
            "timestamp": r.target_timestamp.isoformat() if r.target_timestamp else r.generated_at.isoformat(),
            "route_id": r.route_id,
            "route_short_name": r.route.route_short_name or r.route_long_name or r.name or r.route_id,
            "predicted_passengers": r.predicted_passengers,
            "confidence_score": r.confidence_score,
            "model_version": r.model_version
        } for r in records
    ]

@router.get("/charts/fleet-utilization")
def get_fleet_utilization_chart(
    db: Session = Depends(get_db),
    region: str | None = None,
    depot: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
):
    from app.database.models import OptimizationResult, Route
    start, end = _resolve_window(date_from, date_to)
    q = db.query(OptimizationResult).join(Route, OptimizationResult.route_id == Route.route_id)
    if start and end:
        q = q.filter(OptimizationResult.timestamp >= start, OptimizationResult.timestamp < end)
    q = _apply_route_scope_filter(db, q, OptimizationResult.route_id, region, depot)
    records = q.order_by(OptimizationResult.timestamp.asc()).limit(100).all()
    return [
        {
            "timestamp": r.timestamp.isoformat(),
            "route_id": r.route_id,
            "route_short_name": r.route.route_short_name or r.route_long_name or r.name or r.route_id,
            "route_name": r.route_name or r.route_id,
            "allocated_buses": r.allocated_buses,
            "utilization": _utilization(r.predicted_demand, r.allocated_buses),
            "predicted_demand": r.predicted_demand,
            "model_version": r.model_version
        } for r in records
    ]

# 12. Demand Analytics - Direct table endpoints for frontend
@router.get("/demand-history")
def get_demand_history(
    db: Session = Depends(get_db),
    region: str | None = None,
    depot: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
):
    """
    Direct endpoint for DemandHistory table data.
    Used by AnalyticsDashboard for historical demand charts.
    """
    from app.database.models import DemandHistory
    start, end = _resolve_window(date_from, date_to)
    
    q = db.query(DemandHistory)
    if start and end:
        q = q.filter(DemandHistory.timestamp >= start, DemandHistory.timestamp < end)
    q = _apply_route_scope_filter(db, q, DemandHistory.route_id, region, depot)
    records = q.order_by(DemandHistory.timestamp.asc()).all()
    
    return [
        {
            "timestamp": r.timestamp.isoformat() if r.timestamp else None,
            "route_id": r.route_id,
            "passenger_count": r.passenger_count,
            "occupancy_percent": r.occupancy_percent,
            "weather": r.weather,
            "traffic": r.traffic,
        } for r in records
    ]

@router.get("/forecast-history")
def get_forecast_history(
    db: Session = Depends(get_db),
    region: str | None = None,
    depot: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
):
    """
    Direct endpoint for ForecastHistory table data.
    Used by AnalyticsDashboard for forecast demand charts.
    """
    from app.database.models import ForecastHistory, Route
    start, end = _resolve_window(date_from, date_to)
    
    q = db.query(ForecastHistory).join(Route, ForecastHistory.route_id == Route.route_id)
    if start and end:
        q = q.filter(ForecastHistory.target_timestamp >= start, ForecastHistory.target_timestamp < end)
    q = _apply_route_scope_filter(db, q, ForecastHistory.route_id, region, depot)
    records = q.order_by(ForecastHistory.target_timestamp.asc()).all()
    
    return [
        {
            "generated_at": r.generated_at.isoformat() if r.generated_at else None,
            "target_timestamp": r.target_timestamp.isoformat() if r.target_timestamp else None,
            "route_id": r.route_id,
            "route_short_name": r.route.route_short_name or r.route_long_name or r.name or r.route_id,
            "predicted_passengers": r.predicted_passengers,
            "confidence_score": r.confidence_score,
            "model_version": r.model_version,
        } for r in records
    ]

@router.get("/optimization/results")
def get_optimization_results(
    db: Session = Depends(get_db),
    region: str | None = None,
    depot: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
):
    """
    Direct endpoint for OptimizationResult table data.
    Used by OptimizationInsights for fleet optimization table.
    Returns only the latest optimization record for each route.
    """
    from app.database.models import OptimizationResult, Route
    from sqlalchemy import func
    
    start, end = _resolve_window(date_from, date_to)
    
    # Subquery to find the latest timestamp for each route
    latest_per_route = (
        db.query(
            OptimizationResult.route_id,
            func.max(OptimizationResult.timestamp).label('max_timestamp')
        )
        .join(Route, OptimizationResult.route_id == Route.route_id)
        .filter(OptimizationResult.timestamp >= start, OptimizationResult.timestamp < end)
        .group_by(OptimizationResult.route_id)
        .subquery()
    )
    
    # Join back to get full records for the latest timestamp per route
    q = (
        db.query(OptimizationResult)
        .join(Route, OptimizationResult.route_id == Route.route_id)
        .join(
            latest_per_route,
            (OptimizationResult.route_id == latest_per_route.c.route_id) &
            (OptimizationResult.timestamp == latest_per_route.c.max_timestamp)
        )
    )
    q = _apply_route_scope_filter(db, q, OptimizationResult.route_id, region, depot)
    records = q.order_by(OptimizationResult.timestamp.desc()).all()
    
    return [
        {
            "id": r.id,
            "timestamp": r.timestamp.isoformat() if r.timestamp else None,
            "route_id": r.route_id,
            "route_short_name": r.route.route_short_name or r.route_long_name or r.name or r.route_id,
            "route_name": r.route_name,
            "predicted_demand": r.predicted_demand,
            "allocated_buses": r.allocated_buses,
            "utilization": r.utilization,
            "unserved_demand": r.unserved_demand,
            "objective_score": r.objective_score,
            "priority_level": r.priority_level,
            "recommended_frequency": r.recommended_frequency,
            "model_version": r.model_version,
        } for r in records
    ]