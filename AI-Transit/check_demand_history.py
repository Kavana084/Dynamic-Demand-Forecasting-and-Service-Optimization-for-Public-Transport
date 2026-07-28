import sys
sys.path.insert(0, './backend')
from app.database.connection import SessionLocal
from app.database.models import DemandHistory
from sqlalchemy.sql import func

db = SessionLocal()
results = db.query(
    DemandHistory.route_id,
    func.avg(DemandHistory.passenger_count).label("avg_pax"),
    func.count(DemandHistory.id).label("record_count")
).group_by(DemandHistory.route_id).all()

print(f"{'route_id':<15} {'avg_pax':<10} {'records':<10}")
print("-" * 35)
for r in results:
    print(f"{r.route_id:<15} {round(float(r.avg_pax), 1):<10} {r.record_count:<10}")

db.close()
