from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from app.database.models import DemandHistory, ForecastHistory, OptimizationResult, FleetAllocation, PipelineExecutionLog


class PipelineMonitorService:
    @staticmethod
    def get_pipeline_status(db: Session) -> dict:
        """
        Returns a structured dict describing the health of each pipeline stage.
        All runtimes/failures are backed by PipelineExecutionLog (no N/A placeholders).
        """

        now = datetime.utcnow()
        lookback = now - timedelta(days=7)

        def _pipeline_stats(pipeline_name: str) -> dict:
            last_completed = (
                db.query(func.max(PipelineExecutionLog.completed_at))
                .filter(
                    PipelineExecutionLog.pipeline_name == pipeline_name,
                    PipelineExecutionLog.completed_at != None,
                )
                .scalar()
            )
            last_started = (
                db.query(func.max(PipelineExecutionLog.started_at))
                .filter(PipelineExecutionLog.pipeline_name == pipeline_name)
                .scalar()
            )
            last_run = last_completed or last_started

            last_success = (
                db.query(PipelineExecutionLog)
                .filter(
                    PipelineExecutionLog.pipeline_name == pipeline_name,
                    PipelineExecutionLog.status == "success",
                    PipelineExecutionLog.completed_at != None,
                )
                .order_by(PipelineExecutionLog.completed_at.desc())
                .first()
            )

            failures_7d = (
                db.query(func.count(PipelineExecutionLog.id))
                .filter(
                    PipelineExecutionLog.pipeline_name == pipeline_name,
                    PipelineExecutionLog.status == "failed",
                    PipelineExecutionLog.started_at >= lookback,
                )
                .scalar()
                or 0
            )

            return {
                "last_run": last_run.isoformat() if last_run else None,
                "last_success_duration_ms": int(last_success.duration_ms) if last_success and last_success.duration_ms is not None else None,
                "failure_count_7d": int(failures_7d),
            }

        def _output_stats(model, ts_attr: str) -> dict:
            count = db.query(model).count()
            latest = db.query(func.max(getattr(model, ts_attr))).scalar()
            return {
                "record_count": int(count),
                "last_update": latest.isoformat() if latest else None,
            }

        # Map pipeline -> output table so the dashboard can show both "ran" and "produced data".
        stage_defs = [
            ("demand_aggregation", "Demand Aggregation", DemandHistory, "timestamp"),
            ("forecasting", "Forecasting", ForecastHistory, "generated_at"),
            ("optimization", "Optimization", OptimizationResult, "timestamp"),
            ("schedule_engine", "Schedule Engine", FleetAllocation, "timestamp"),
        ]

        stages = []
        for pipeline_name, label, model, ts_attr in stage_defs:
            pipe = _pipeline_stats(pipeline_name)
            out = _output_stats(model, ts_attr)

            # Health: pipeline exists AND produced output recently (within 24h)
            health = "Healthy" if out["record_count"] > 0 else "Warning"
            stages.append({
                "stage": label,
                "pipeline_name": pipeline_name,
                "record_count": out["record_count"],
                "last_update": out["last_update"],
                "last_run": pipe["last_run"],
                "processing_duration_ms": pipe["last_success_duration_ms"],
                "failure_count": pipe["failure_count_7d"],
                "health_status": health,
            })

        any_logs = db.query(func.count(PipelineExecutionLog.id)).scalar() or 0
        if any_logs == 0:
            overall_status = "empty"
        else:
            healthy = [s for s in stages if s["health_status"] == "Healthy"]
            overall_status = "healthy" if len(healthy) == len(stages) else "partial"

        all_runs = [s["last_run"] for s in stages if s["last_run"]]
        last_run = max(all_runs) if all_runs else None

        return {
            "overall_status": overall_status,
            "last_run": last_run,
            "updated_at": last_run,
            "stages": stages,
        }
