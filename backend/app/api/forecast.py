from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.schemas.forecast import ForecastRequest, ForecastResponse
from app.services.forecast_service import ForecastService
from app.database.db import get_db
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/forecast", response_model=ForecastResponse, status_code=status.HTTP_200_OK)
def create_forecast(request: ForecastRequest, db: Session = Depends(get_db)):
    logger.info(f"Received forecast request for route_id={request.route_id}, stop_id={request.stop_id}")
    try:
        predicted_count = ForecastService.generate_forecast(db, request)
        return ForecastResponse(predicted_passenger_count=predicted_count)
    except ValueError as ve:
        if "Feature data not available" in str(ve):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error during forecast generation")