import logging
import datetime
from app.database.connection import SessionLocal
from app.database.models import ModelMetadata

logger = logging.getLogger(__name__)

class ModelMetadataService:
    def __init__(self):
        pass

    def populate_if_empty(self, prediction_service):
        """
        Extracts available metadata from the loaded CatBoost model and
        populates the ModelMetadata table if it is empty.
        Leaves metrics as NULL if they are not natively available.
        """
        if not prediction_service or not prediction_service.model:
            logger.warning("ModelMetadataService: No model loaded in prediction_service.")
            return

        db = SessionLocal()
        try:
            # Check if metadata already exists
            existing = db.query(ModelMetadata).first()
            if existing:
                logger.info("ModelMetadataService: Metadata already exists. Skipping population.")
                return

            # Extract metadata from CatBoost model
            model = prediction_service.model
            
            # CatBoost specific properties
            try:
                params = model.get_params()
                version = "catboost-v2" # Default version naming
                
                # We do not fabricate r2_score, rmse, or mae if we don't have them
                # unless they were stored in the model's user_defined_metrics or attributes (rare)
                
                new_meta = ModelMetadata(
                    model_name="CatBoost Demand Forecaster",
                    version=version,
                    trained_at=datetime.datetime.utcnow(),
                    r2_score=None,
                    rmse=None,
                    mae=None,
                    dataset_size=None,
                    is_active=True
                )
                
                db.add(new_meta)
                db.commit()
                logger.info("ModelMetadataService: Successfully populated model_metadata table.")
            except Exception as e:
                logger.error(f"Failed to extract parameters from model: {e}")

        except Exception as e:
            logger.error(f"ModelMetadataService database error: {e}")
            db.rollback()
        finally:
            db.close()

    def populate_catboost_metadata(self, model_loader):
        """
        Populate model metadata from CatBoost model loader with training metrics.
        
        This method extracts metadata from the model_loader including:
        - Training metrics (RMSE, MAE, R², MAPE)
        - Model configuration
        - Feature count
        
        Args:
            model_loader: ModelLoader instance with loaded CatBoost model
        """
        if not model_loader or not model_loader.is_model_loaded():
            logger.warning("ModelMetadataService: CatBoost model not loaded.")
            return

        db = SessionLocal()
        try:
            # Check if metadata already exists
            existing = db.query(ModelMetadata).first()
            if existing:
                logger.info("ModelMetadataService: Metadata already exists. Skipping population.")
                return

            # Get training metrics from model_loader
            training_metrics = model_loader.get_training_metrics()
            model_config = model_loader.get_model_config()
            
            # Extract metrics
            rmse = training_metrics.get('RMSE')
            mae = training_metrics.get('MAE')
            r2_score = training_metrics.get('R2')
            mape = training_metrics.get('MAPE')
            
            # Extract dataset size from config
            dataset_size = model_config.get('dataset_size')
            
            # Extract training date from config
            training_date_str = model_config.get('training_date')
            trained_at = datetime.datetime.utcnow()
            if training_date_str:
                try:
                    trained_at = datetime.datetime.fromisoformat(training_date_str)
                except Exception:
                    pass
            
            # Create metadata record
            new_meta = ModelMetadata(
                model_name="CatBoost Demand Forecaster",
                version="catboost-v3",
                trained_at=trained_at,
                r2_score=r2_score,
                rmse=rmse,
                mae=mae,
                dataset_size=dataset_size,
                is_active=True
            )
            
            db.add(new_meta)
            db.commit()
            
            logger.info(
                f"ModelMetadataService: Successfully populated CatBoost metadata. "
                f"RMSE={rmse}, MAE={mae}, R²={r2_score}, Dataset Size={dataset_size}"
            )
            
        except Exception as e:
            logger.error(f"ModelMetadataService database error: {e}", exc_info=True)
            db.rollback()
        finally:
            db.close()

model_metadata_service = ModelMetadataService()
