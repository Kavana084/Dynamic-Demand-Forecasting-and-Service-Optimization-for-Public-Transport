from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from app.database.models import DemandHistory, WeatherRecord, OptimizationResult, GTFSStop, PipelineExecutionLog

class DataQualityService:
    @staticmethod
    def get_data_quality(db: Session):
        # Completeness (40%)
        # Missing demand records, weather, predictions.
        # We can proxy this by checking if tables are empty or looking at the last few hours.
        total_demand = db.query(DemandHistory).count()
        missing_weather = db.query(DemandHistory).filter(DemandHistory.weather == None).count()
        
        completeness_score = 100
        if total_demand > 0:
            completeness_score = max(0, 100 - (missing_weather / total_demand * 100))
            
        # Freshness (30%)
        # How recent is the latest data
        from datetime import datetime, timedelta
        latest_demand = db.query(func.max(DemandHistory.timestamp)).scalar()
        
        freshness_score = 100
        if latest_demand:
            if isinstance(latest_demand, str):
                try:
                    latest_demand = datetime.fromisoformat(latest_demand)
                except:
                    pass
            if isinstance(latest_demand, datetime):
                hours_old = (datetime.utcnow() - latest_demand).total_seconds() / 3600
                if hours_old > 24:
                    freshness_score = 50
                if hours_old > 48:
                    freshness_score = 0
        else:
            freshness_score = 0
            
        # Consistency (20%)
        # Pipeline execution failures (real tracking via PipelineExecutionLog).
        lookback = datetime.utcnow() - timedelta(days=7)
        total_opts = db.query(OptimizationResult).count()
        failed_opts = (
            db.query(func.count(PipelineExecutionLog.id))
            .filter(
                PipelineExecutionLog.pipeline_name == "optimization",
                PipelineExecutionLog.status == "failed",
                PipelineExecutionLog.started_at >= lookback,
            )
            .scalar()
            or 0
        )
        consistency_score = 100
        if total_opts > 0:
            consistency_score = max(0, 100 - (failed_opts / total_opts * 100))
            
        # Integrity (10%)
        # GTFS Stops count
        gtfs_stops = db.query(GTFSStop).count()
        integrity_score = 100 if gtfs_stops > 0 else 0
        
        overall_score = (completeness_score * 0.4) + (freshness_score * 0.3) + (consistency_score * 0.2) + (integrity_score * 0.1)
        
        return {
            "overall_score": round(overall_score, 1),
            "completeness_score": round(completeness_score, 1),
            "freshness_score": round(freshness_score, 1),
            "consistency_score": round(consistency_score, 1),
            "integrity_score": round(integrity_score, 1),
            "details": {
                "missing_weather_records": missing_weather,
                "optimization_failures": failed_opts,
                "gtfs_stops": gtfs_stops
            }
        }
