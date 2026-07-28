from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database.models import ForecastHistory, DemandHistory, ModelMetadata
import math

class ForecastAlignmentService:
    @staticmethod
    def get_alignment_report(db: Session):
        # 1. Check schemas via count to see if we have data
        pred_count = db.query(ForecastHistory).count()
        demand_count = db.query(DemandHistory).count()
        
        # 2. Match records
        # Join on route_id and timestamp rounded to hour
        matches = db.query(
            ForecastHistory.predicted_passengers,
            DemandHistory.passenger_count
        ).join(
            DemandHistory,
            (ForecastHistory.route_id == DemandHistory.route_id) & 
            (func.strftime('%Y-%m-%d %H', ForecastHistory.target_timestamp) == func.strftime('%Y-%m-%d %H', DemandHistory.timestamp))
        ).all()
        
        aligned_count = len(matches)
        
        rmse = None
        mae = None
        mape = None
        accuracy = None
        
        if aligned_count > 0:
            squared_error_sum = 0
            absolute_error_sum = 0
            percentage_error_sum = 0
            
            for pred, actual in matches:
                error = pred - actual
                squared_error_sum += error ** 2
                absolute_error_sum += abs(error)
                if actual > 0:
                    percentage_error_sum += abs(error) / actual
                
            rmse = math.sqrt(squared_error_sum / aligned_count)
            mae = absolute_error_sum / aligned_count
            mape = (percentage_error_sum / aligned_count) * 100
            
            # Simple accuracy metric: 100 - MAPE (bounded at 0)
            accuracy = max(0, 100 - mape)
            
        # Get Model Metadata
        model_meta = db.query(ModelMetadata).filter(ModelMetadata.is_active == True).first()
        model_version = model_meta.version if model_meta else "Unavailable"
        last_training = model_meta.trained_at if model_meta else None
        
        return {
            "alignment_status": {
                "prediction_records_count": pred_count,
                "demand_history_count": demand_count,
                "aligned_records_count": aligned_count,
                "is_aligned": aligned_count > 0
            },
            "performance_metrics": {
                "rmse": round(rmse, 2) if rmse is not None else None,
                "mae": round(mae, 2) if mae is not None else None,
                "mape": round(mape, 2) if mape is not None else None,
                "accuracy": round(accuracy, 2) if accuracy is not None else None,
                "model_version": model_version,
                "last_training_timestamp": last_training
            }
        }
