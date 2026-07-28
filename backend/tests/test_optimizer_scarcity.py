import pytest
from app.optimization import optimize_fleet

def test_global_fleet_size_constraint():
    """
    Test that the MILP optimization respects the global fleet size constraint.
    If total demand requires more buses than max_total_buses, the optimizer
    must not exceed max_total_buses, leaving some unmet demand.
    """
    # 5 routes, each needs 120 passengers. Bus capacity = 60.
    # Total required buses for 0 unmet demand = 10 buses (2 per route).
    route_demands = {
        "route_1": 120,
        "route_2": 120,
        "route_3": 120,
        "route_4": 120,
        "route_5": 120,
    }

    # We restrict the total fleet to 6 buses.
    result = optimize_fleet(
        route_demands=route_demands,
        bus_capacity=60,
        max_buses_per_route=5,
        max_total_buses=6,
        alpha=1.0,
        beta=0.7,
        gamma=2.0,
        delta=1.5
    )

    assert result["status"] == "Optimal", f"Solver did not find optimal solution: {result['status']}"

    # Verify that exactly 6 buses were used (or fewer, but shouldn't be given high demand penalty)
    total_buses_used = result["summary"]["total_buses_used"]
    assert total_buses_used == 6, f"Expected 6 buses used, but got {total_buses_used}"

    # Verify there is unmet demand (total demand 600 - total capacity 360 = 240 unmet)
    total_unmet_demand = result["summary"]["total_unmet_demand"]
    assert total_unmet_demand == 240, f"Expected 240 unmet demand, but got {total_unmet_demand}"
