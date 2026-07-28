import sys
sys.path.insert(0, "f:/transit-ai-system/backend")

from app.database.connection import SessionLocal
from app.database.models import GTFSStop

db = SessionLocal()
try:
    stops = db.query(GTFSStop).limit(10).all()
    print("STOP_ID | STOP_NAME")
    for s in stops:
        print(f"{s.stop_id} | {s.stop_name}")
finally:
    db.close()
