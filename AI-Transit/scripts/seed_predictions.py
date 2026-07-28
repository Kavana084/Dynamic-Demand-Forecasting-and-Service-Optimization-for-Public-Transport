from sqlalchemy import text
from app.database.connection import engine
from datetime import datetime

# Grab the first valid route from your db to avoid foreign key errors
with engine.begin() as conn:
    result = conn.execute(text("SELECT route_id FROM routes LIMIT 1")).fetchone()
    if not result:
        print("Your routes table is empty. Please add a route first!")
    else:
        valid_route = result[0]
        now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        
        # Insert some dummy predictions
        sql = f"""
        INSERT INTO prediction_records (timestamp, route_id, predicted_passengers, confidence_score, model_version)
        VALUES 
        ('{now}', '{valid_route}', 45, 0.88, 'catboost-v1'),
        ('{now}', '{valid_route}', 60, 0.92, 'catboost-v1'),
        ('{now}', '{valid_route}', 32, 0.85, 'catboost-v1');
        """
        conn.execute(text(sql))
        print("Successfully seeded 3 predictions! Your dashboard will now show 137 predictedDemand.")
