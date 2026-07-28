import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.connection import SessionLocal
from app.services.routing_service import resolve_route_dynamic

def test_routing():
    db = SessionLocal()
    try:
        source = "22890"
        dest = "20940"
        print(f"Testing route {source} -> {dest}...")
        res = resolve_route_dynamic(db, source, dest)
        print("ROUTE RESOLVED SUCCESSFULLY")
    except Exception as e:
        import traceback
        print("ROUTING FAILED!")
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_routing()
