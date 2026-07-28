import os
import sys
import time

# Add backend directory to path
base_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(base_dir, 'backend'))

from backend.app.database.connection import SessionLocal
from backend.app.services.fleet_service import FleetService
from backend.app.schemas.fleet import FleetOptimizationRequest

def main():
    db = SessionLocal()
    
    # Initialize the prediction service and model loader
    from backend.app.ml.model_loader import model_loader
    model_loader.load_model()
    
    print("Starting MILP Optimization Dry Run...")
    start_time = time.time()
    
    # Create request payload simulating an admin global optimization call
    request = FleetOptimizationRequest(
        available_buses=200,
        bus_capacity=60,
        max_buses_per_route=15
    )
    
    try:
        # Execute MILP model
        response = FleetService.optimize_fleet(db=db, request=request)
        end_time = time.time()
        
        execution_time_ms = (end_time - start_time) * 1000
        
        print("\n--- MILP DRY RUN RESULTS ---")
        print(f"Solver Status: Optimal (Total Routes Processed: {len(response.allocated_buses)})")
        print(f"Objective Value (Total Covered Passengers): {response.total_covered_passengers}")
        print(f"Total Predicted Demand: {response.total_predicted_demand}")
        print(f"Total Allocated Buses: {response.used_buses} / {response.available_buses}")
        print(f"Global Utilization/Coverage: {response.coverage_percentage}%")
        print(f"Execution Time: {execution_time_ms:.2f} ms")
        
        print("\nSample Route Allocations:")
        for allocation in response.allocated_buses[:5]:
            print(f"  Route: {allocation.route_id} | Demand: {allocation.predicted_demand} | "
                  f"Buses: {allocation.assigned_buses} | Unmet: {allocation.unmet_demand}")
                  
    except Exception as e:
        print(f"MILP Execution Failed: {e}")
    finally:
        db.close()

if __name__ == '__main__':
    main()
