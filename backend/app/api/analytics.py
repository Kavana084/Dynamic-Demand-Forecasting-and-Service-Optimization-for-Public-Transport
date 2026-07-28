from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import List
from app.schemas.analytics import TotalPredictionsResponse, AverageDemandResponse, TopRouteItem, DashboardSummaryResponse
from app.services.analytics_service import AnalyticsService
from app.database.db import get_db
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/total-predictions", response_model=TotalPredictionsResponse, status_code=status.HTTP_200_OK)
def get_total_predictions(db: Session = Depends(get_db)):
    logger.info("Received request for total predictions analytics")
    return AnalyticsService.get_total_predictions(db)

@router.get("/average-demand", response_model=AverageDemandResponse, status_code=status.HTTP_200_OK)
def get_average_demand(db: Session = Depends(get_db)):
    logger.info("Received request for average demand analytics")
    return AnalyticsService.get_average_demand(db)

@router.get("/top-routes", response_model=List[TopRouteItem], status_code=status.HTTP_200_OK)
def get_top_routes(db: Session = Depends(get_db)):
    logger.info("Received request for top routes analytics")
    return AnalyticsService.get_top_routes(db)

@router.get("/dashboard", response_model=DashboardSummaryResponse, status_code=status.HTTP_200_OK)
def get_dashboard_summary(db: Session = Depends(get_db)):
    logger.info("Received request for dashboard summary analytics")
    return AnalyticsService.get_dashboard_summary(db)
