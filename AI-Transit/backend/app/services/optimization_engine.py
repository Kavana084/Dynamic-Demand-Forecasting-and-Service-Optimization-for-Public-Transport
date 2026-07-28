import logging
from sqlalchemy.orm import Session
from app.database.models import ForecastHistory, Route
from app.optimization import optimize_fleet
from app.database.crud import create_optimization_result
from app.schemas.fleet import FleetOptimizationResponse, AllocatedBusItem

logger = logging.getLogger(__name__)

class OptimizationEngine:
    @staticmethod
    def run(db: Session, available_buses: int = 1000, bus_capacity: int = 60, max_buses_per_route: int = 15) -> FleetOptimizationResponse:
        logger.info("Running unified MILP optimization engine")
        
        # 1. Load latest ForecastHistory prediction per route
        latest_forecasts = db.query(ForecastHistory).order_by(ForecastHistory.generated_at.desc()).limit(100).all()
        active_forecasts = {}
        for f in latest_forecasts:
            if f.route_id not in active_forecasts:
                active_forecasts[f.route_id] = f

        # Get route names
        routes = db.query(Route).all()
        route_names = {r.route_id: (r.route_short_name or r.route_long_name or r.name or r.route_id) for r in routes}

        route_demands = {}
        for route_id, f_record in active_forecasts.items():
            route_demands[route_id] = f_record.route_predicted_passengers or 0

        if not route_demands:
            logger.warning("No forecast data available for optimization")
            return FleetOptimizationResponse(
                available_buses=available_buses,
                used_buses=0,
                total_predicted_demand=0,
                total_covered_passengers=0,
                coverage_percentage=0.0,
                allocated_buses=[]
            )

        # Execute optimize_fleet()
        milp_response = optimize_fleet(
            route_demands=route_demands,
            bus_capacity=bus_capacity,
            max_buses_per_route=max_buses_per_route,
            cost_per_bus=1000.0,
            penalty_unmet_demand=50.0,
            alpha=1.0,
            beta=0.7,
            gamma=2.0,
            delta=1.5
        )

        if milp_response.get("status") == "error":
            logger.error(f"MILP failed: {milp_response.get('error_details')}")
            return FleetOptimizationResponse(
                available_buses=available_buses,
                used_buses=0,
                total_predicted_demand=sum(route_demands.values()),
                total_covered_passengers=0,
                coverage_percentage=0.0,
                allocated_buses=[]
            )

        opt_breakdown = milp_response.get("route_allocation", [])
        
        allocated_items = []
        used_buses = 0
        total_covered = 0
        total_predicted = sum(route_demands.values())

        for opt_data in opt_breakdown:
            r_id = opt_data.get("route_id")
            allocated_buses_count = opt_data.get("buses_assigned", 0)
            demand = opt_data.get("demand", 0)
            unmet = opt_data.get("unmet_demand", 0)
            util = opt_data.get("utilization_percent", 0.0)

            priority = "MEDIUM"
            if unmet > 10:
                priority = "HIGH"
            elif unmet == 0 and util > 70:
                priority = "LOW"

            freq_rec = "Maintain current frequency"
            if unmet > 0:
                freq_rec = f"Increase frequency - {unmet} passengers unserved"
            elif util < 50 and allocated_buses_count > 0:
                freq_rec = "Decrease frequency - low utilization"
                
            r_name = route_names.get(r_id, r_id)
            
            allocated_items.append(AllocatedBusItem(
                route_id=r_id,
                route_name=r_name,
                predicted_demand=demand,
                assigned_buses=allocated_buses_count,
                utilization_percent=util,
                unmet_demand=unmet,
                priority=priority,
                recommended_frequency=freq_rec
            ))
            
            used_buses += allocated_buses_count
            total_covered += max(0, demand - unmet)

            create_optimization_result(
                db=db,
                route_id=r_id,
                route_name=r_name,
                allocated_buses=allocated_buses_count,
                utilization=util,
                objective_score=util,
                unserved_demand=unmet,
                priority_level=priority,
                recommended_frequency=freq_rec,
                predicted_demand=demand,
                model_version="catboost+demand_adjusted"
            )

        coverage_percentage = (total_covered / total_predicted * 100) if total_predicted > 0 else 0.0

        return FleetOptimizationResponse(
            available_buses=available_buses,
            used_buses=used_buses,
            total_predicted_demand=total_predicted,
            total_covered_passengers=total_covered,
            coverage_percentage=round(coverage_percentage, 2),
            allocated_buses=allocated_items
        )
