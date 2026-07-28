from app.database.connection import SessionLocal
from app.database.models import JourneyHistory, DemandHistory, ForecastHistory, OptimizationResult, PipelineRun

def check():
    db = SessionLocal()
    try:
        print("JourneyHistory count:", db.query(JourneyHistory).count())
    except Exception as e:
        print("JourneyHistory error:", e)
        db.rollback()

    try:
        print("DemandHistory count:", db.query(DemandHistory).count())
    except Exception as e:
        print("DemandHistory error:", e)
        db.rollback()

    try:
        print("ForecastHistory count:", db.query(ForecastHistory).count())
    except Exception as e:
        print("ForecastHistory error:", e)
        db.rollback()

    try:
        print("OptimizationResult count:", db.query(OptimizationResult).count())
    except Exception as e:
        print("OptimizationResult error:", e)
        db.rollback()

    try:
        print("PipelineRun count:", db.query(PipelineRun).count())
    except Exception as e:
        print("PipelineRun error:", e)
        db.rollback()

if __name__ == "__main__":
    check()
