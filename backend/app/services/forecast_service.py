import logging
from datetime import datetime
from sqlalchemy.orm import Session
from app.schemas.forecast import ForecastRequest
from app.ml.predictor import Predictor
from app.database.models import PredictionRecord, RouteFeature, ForecastHistory

logger = logging.getLogger(__name__)

class ForecastService:
    @staticmethod
    def generate_forecast(db: Session, request: ForecastRequest) -> int:
        try:
            # 1. Get latest RouteFeature
            route_feature = db.query(RouteFeature).filter(
                RouteFeature.route_id == request.route_id,
                RouteFeature.stop_id == request.stop_id
            ).order_by(RouteFeature.updated_at.desc()).first()
            
            if not route_feature:
                logger.warning(f"Feature data not available for route {request.route_id} and stop {request.stop_id}")
                raise ValueError("Feature data not available for this route and stop")

            # 2. Derive time features
            now = datetime.now()
            current_hour = now.hour
            current_weekday = now.weekday()

            logger.info(f"Generating forecast for route={request.route_id}, stop={request.stop_id}")

            # 3. Call Predictor
            predicted_float = Predictor.predict_passenger_count(
                route_id=request.route_id,
                stop_id=request.stop_id,
                hour=current_hour,
                weekday=current_weekday,
                weather=route_feature.weather,
                temperature=route_feature.temperature,
                rainfall=route_feature.rainfall,
                delay_minutes=route_feature.delay_minutes,
                congestion_score=route_feature.congestion_score
            )
            
            predicted_count = int(round(predicted_float))
            
            # 4. Save prediction to database
            record = ForecastHistory(
                route_id=request.route_id,
                target_timestamp=now,
                route_predicted_passengers=predicted_count,
                confidence_score=0.9, # default since predictor doesn't return it here
                model_version="heuristic"
            )
            db.add(record)
            db.commit()
            db.refresh(record)
            
            logger.info(f"Forecast generated: {predicted_count} passengers.")
            return predicted_count
            
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Forecast generation failed: {e}")
            db.rollback()
            raise