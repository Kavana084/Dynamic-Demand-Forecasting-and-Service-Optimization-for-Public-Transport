from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.schemas.fleet import FleetRecommendationRequest, FleetRecommendationResponse, FleetOptimizationRequest, FleetOptimizationResponse
from app.services.fleet_service import FleetService
from app.database.connection import get_db
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/recommendation", response_model=FleetRecommendationResponse, status_code=status.HTTP_200_OK)
def create_fleet_recommendation(request: FleetRecommendationRequest, db: Session = Depends(get_db)):
    logger.info(f"Received fleet recommendation request for route_id={request.route_id}, stop_id={request.stop_id}")
    try:
        recommendation = FleetService.generate_recommendation(db, request)
        return recommendation
    except ValueError as ve:
        if "Feature data not available" in str(ve):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        logger.error(f"Internal server error in fleet recommendation: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error during recommendation generation")

@router.post("/optimize", response_model=FleetOptimizationResponse, status_code=status.HTTP_200_OK)
def optimize_fleet(request: FleetOptimizationRequest, db: Session = Depends(get_db)):
    logger.info(f"Received fleet optimization request for {request.available_buses} buses")
    try:
        optimization = FleetService.optimize_fleet(db, request)
        return optimization
    except Exception as e:
        logger.error(f"Internal server error in fleet optimization: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error during fleet optimization")
