from fastapi import APIRouter, Request, Depends
from sqlalchemy.orm import Session
from app.database.connection import get_db
import os
from app.cache import app_cache
from app.logger import app_logger
from app.database.models import OptimizationResult

router = APIRouter()

@router.get("/api/health")
def get_health(request: Request, db: Session = Depends(get_db)):
    from sqlalchemy import func
    from app.database.models import ForecastHistory
    import datetime

    # Mock window for testing (today)
    today = datetime.datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    start, end = today, today + datetime.timedelta(days=1)
    
    # Run the current subquery logic
    time_field = ForecastHistory.target_timestamp
    model_class = ForecastHistory
    
    subq = db.query(
        model_class.route_id,
        func.max(time_field).label('max_time')
    ).filter(
        time_field >= start,
        time_field < end
    ).group_by(model_class.route_id).subquery()
    
    q = db.query(model_class).join(
        subq,
        (model_class.route_id == subq.c.route_id) &
        (time_field == subq.c.max_time)
    )

    sql_statement = str(q.statement.compile(compile_kwargs={"literal_binds": True}))
    
    rows = q.all()
    intermediate_rows = [{"id": r.id, "route": r.route_id, "target": str(r.target_timestamp), "generated": str(r.generated_at), "passengers": r.predicted_passengers} for r in rows]
    total = sum(r.predicted_passengers for r in rows)

    return {
        "sql": sql_statement,
        "rows": intermediate_rows,
        "total": total
    }
