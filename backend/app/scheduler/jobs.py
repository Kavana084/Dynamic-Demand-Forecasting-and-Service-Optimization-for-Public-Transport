import logging
import random
from apscheduler.schedulers.background import BackgroundScheduler
from app.database.db import SessionLocal
from app.database.models import RouteFeature
from datetime import datetime

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()

ROUTE_STOPS_CONFIG = {
    "R101": ["S205", "S206"],
    "R102": ["S301", "S302"]
}

def update_route_features():
    logger.info("Executing scheduled job: update_route_features...")
    db = SessionLocal()
    try:
        weather_options = ["Sunny", "Cloudy", "Rainy"]
        
        for route_id, stops in ROUTE_STOPS_CONFIG.items():
            for stop_id in stops:
                # Simulate features
                weather = random.choice(weather_options)
                temperature = round(random.uniform(15.0, 35.0), 1)
                
                # If rainy, simulate rainfall, otherwise 0
                rainfall = round(random.uniform(1.0, 10.0), 1) if weather == "Rainy" else 0.0
                
                delay_minutes = round(random.uniform(0.0, 15.0), 1)
                congestion_score = round(random.uniform(1.0, 5.0), 2)
                
                logger.info(f"Generated features for {route_id}-{stop_id}: weather={weather}, temp={temperature}")

                # Upsert
                existing_feature = db.query(RouteFeature).filter(
                    RouteFeature.route_id == route_id,
                    RouteFeature.stop_id == stop_id
                ).first()
                
                if existing_feature:
                    existing_feature.weather = weather
                    existing_feature.temperature = temperature
                    existing_feature.rainfall = rainfall
                    existing_feature.delay_minutes = delay_minutes
                    existing_feature.congestion_score = congestion_score
                    existing_feature.updated_at = datetime.now()
                else:
                    new_feature = RouteFeature(
                        route_id=route_id,
                        stop_id=stop_id,
                        weather=weather,
                        temperature=temperature,
                        rainfall=rainfall,
                        delay_minutes=delay_minutes,
                        congestion_score=congestion_score
                    )
                    db.add(new_feature)
        
        db.commit()
        logger.info("Successfully updated route features in database.")
    except Exception as e:
        logger.error(f"Error in update_route_features job: {e}")
        db.rollback()
    finally:
        db.close()

def start_scheduler():
    if not scheduler.running:
        scheduler.add_job(update_route_features, 'cron', minute='0,30')
        scheduler.start()
        logger.info("APScheduler started.")

def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown()
        logger.info("APScheduler stopped.")
