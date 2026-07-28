import os
import sys

# Ensure backend directory is in the path
base_dir = os.path.dirname(os.path.abspath(__file__))
if base_dir not in sys.path:
    sys.path.append(base_dir)

from app.database.connection import SessionLocal
from app.database.models import JourneyHistory, DemandHistory, ForecastHistory, OptimizationResult, PipelineRun

def check():
    db = SessionLocal()
    results = []
    
    for model in [JourneyHistory, DemandHistory, ForecastHistory, OptimizationResult, PipelineRun]:
        try:
            count = db.query(model).count()
            results.append(f"{model.__name__} count: {count}")
        except Exception as e:
            results.append(f"{model.__name__} error: {e}")
            db.rollback()

    with open("f:\\transit-ai-system\\backend\\test_results.txt", "w") as f:
        f.write("\n".join(results))

if __name__ == "__main__":
    check()
