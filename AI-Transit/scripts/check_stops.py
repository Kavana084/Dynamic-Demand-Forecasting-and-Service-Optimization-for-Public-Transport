from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import sys
import os

sys.path.append(os.path.abspath("f:/transit-ai-system/backend"))
from app.database.models import GTFSStop
from dotenv import load_dotenv

load_dotenv("f:/transit-ai-system/backend/.env")

engine = create_engine(os.getenv("MYSQL_DATABASE_URL"))
Session = sessionmaker(bind=engine)
db = Session()

majestic = db.query(GTFSStop.stop_name).filter(GTFSStop.stop_name.ilike("%Majestic%")).all()
whitefield = db.query(GTFSStop.stop_name).filter(GTFSStop.stop_name.ilike("%Whitefield%")).all()

with open("f:/transit-ai-system/stops_output.txt", "w") as f:
    f.write(f"Majestic stops: {majestic}\n")
    f.write(f"Whitefield stops: {whitefield}\n")

    all_stops = db.query(GTFSStop.stop_name).limit(20).all()
    f.write(f"Sample 20 stops: {all_stops}\n")
