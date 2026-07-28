import math
import psutil
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from app.database.models import ForecastHistory, OptimizationResult, PipelineExecutionLog

# Must match DEFAULT_BUS_CAPACITY in api/admin.py so fleet_availability
# is computed on the same assumptions as optimization insights.
_DEFAULT_BUS_CAPACITY = 50


def _compute_fleet_availability(db: Session):
    """
    Fleet availability = percentage of routes whose latest allocated fleet
    meets or exceeds the demand-derived requirement.

    Formula per route:
        required  = ceil(predicted_demand / BUS_CAPACITY)
        covered   = allocated_buses >= required

    Returns a float 0–100, or None if no optimization results exist yet.
    """
    recent = (
        db.query(OptimizationResult)
        .order_by(OptimizationResult.timestamp.desc())
        .limit(200)
        .all()
    )
    if not recent:
        return None

    adequate = 0
    for r in recent:
        demand = int(r.predicted_demand or 0)
        allocated = int(r.allocated_buses or 0)
        if demand <= 0:
            # No demand forecast → treat as covered
            adequate += 1
            continue
        required = math.ceil(demand / max(1, _DEFAULT_BUS_CAPACITY))
        if allocated >= required:
            adequate += 1

    return round((adequate / len(recent)) * 100, 1)


class SystemMonitorService:
    @staticmethod
    def get_system_health(db: Session) -> dict:
        """
        Returns system health with flat top-level fields that the AdminDashboard
        UI reads, plus the original nested structure for backward compatibility.

        Flat fields (used by OperationalHealthWidgets and the Fleet Availability KPI):
          status           : "healthy" | "degraded"
          message          : human-readable status description
          fleet_availability: float 0-100, or null when no optimization data exists

        Nested structure (preserved for any consumers that already use it):
          infrastructure   : { api_status, database_status, cpu_usage, memory_usage }
          ai_services      : { forecast_service_status, optimization_service_status, ... }
          historical       : { forecast_runs_7d, optimization_runs_7d, ... }
        """
        # ── Infrastructure ────────────────────────────────────────────────────
        cpu_usage    = psutil.cpu_percent(interval=None)
        memory       = psutil.virtual_memory()
        memory_usage = memory.percent

        # ── AI Service availability (derived from DB records) ─────────────────
        last_forecast     = db.query(func.max(ForecastHistory.generated_at)).scalar()
        last_optimization = db.query(func.max(OptimizationResult.timestamp)).scalar()

        forecast_status = "Healthy" if last_forecast     else "Unavailable"
        opt_status      = "Healthy" if last_optimization else "Unavailable"

        # ── Volume totals (simplified; used as proxy for 7-day counts) ────────
        forecast_runs     = db.query(ForecastHistory).count()
        optimization_runs = db.query(OptimizationResult).count()

        # ── Derive flat status / message ──────────────────────────────────────
        both_healthy = forecast_status == "Healthy" and opt_status == "Healthy"
        if both_healthy:
            status  = "healthy"
            message = "All AI services and database are operating normally."
        elif forecast_status == "Healthy" or opt_status == "Healthy":
            status  = "degraded"
            message = "One or more AI services are awaiting data."
        else:
            status  = "degraded"
            message = "No forecast or optimization records found. Run the pipeline to populate."

        # ── Fleet availability (real computation from OptimizationResult) ──────
        fleet_availability = _compute_fleet_availability(db)

        return {
            # ── Flat contract (read by AdminDashboard.jsx useMemo + KPI card) ──
            "status":            status,
            "message":           message,
            "fleet_availability": fleet_availability,   # None → UI renders "—"

            # ── Nested structure (preserved for backward compat) ───────────────
            "infrastructure": {
                "api_status":      "Online",
                "database_status": "Online",
                "cpu_usage":       cpu_usage,
                "memory_usage":    memory_usage,
            },
            "ai_services": {
                "forecast_service_status":    forecast_status,
                "optimization_service_status": opt_status,
                "prediction_throughput":      forecast_runs,
                "optimization_throughput":    optimization_runs,
                "last_forecast_run":          last_forecast,
                "last_optimization_run":      last_optimization,
            },
            "historical": {
                # Simplified totals; not filtered to 7 days (no created_at on these tables).
                "forecast_runs_7d":       forecast_runs,
                "optimization_runs_7d":   optimization_runs,
                # Failures + runtimes are backed by PipelineExecutionLog.
                "prediction_failures": int(
                    db.query(func.count(PipelineExecutionLog.id))
                    .filter(
                        PipelineExecutionLog.pipeline_name == "forecasting",
                        PipelineExecutionLog.status == "failed",
                        PipelineExecutionLog.started_at >= datetime.utcnow() - timedelta(days=7),
                    )
                    .scalar()
                    or 0
                ),
                "optimization_failures": int(
                    db.query(func.count(PipelineExecutionLog.id))
                    .filter(
                        PipelineExecutionLog.pipeline_name == "optimization",
                        PipelineExecutionLog.status == "failed",
                        PipelineExecutionLog.started_at >= datetime.utcnow() - timedelta(days=7),
                    )
                    .scalar()
                    or 0
                ),
                "average_runtime_ms": (
                    float(
                        db.query(func.avg(PipelineExecutionLog.duration_ms))
                        .filter(
                            PipelineExecutionLog.pipeline_name.in_(["demand_aggregation", "forecasting", "optimization"]),
                            PipelineExecutionLog.status == "success",
                            PipelineExecutionLog.duration_ms != None,
                            PipelineExecutionLog.started_at >= datetime.utcnow() - timedelta(days=7),
                        )
                        .scalar()
                        or 0.0
                    )
                    or None
                ),
            },
        }
