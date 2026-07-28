import sys, json
sys.path.append('backend')
from app.database.connection import SessionLocal
from app.database.models import OptimizationResult
from app.schemas.fleet import FleetOptimizationRequest
from app.services.fleet_service import FleetService
from app.api.admin import get_overview_kpis

db = SessionLocal()

count_before = db.query(OptimizationResult).count()

req = FleetOptimizationRequest(available_buses=1000, bus_capacity=60, max_buses_per_route=15)
res = FleetService.optimize_fleet(db, req)

count_after = db.query(OptimizationResult).count()

kpis = get_overview_kpis(db=db)

print("FLEET_OPT:", res.dict())
print(f"BEFORE: {count_before} AFTER: {count_after}")
print("KPI:", kpis)
