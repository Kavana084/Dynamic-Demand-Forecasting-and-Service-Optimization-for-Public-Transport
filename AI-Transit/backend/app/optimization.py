"""
optimization.py — MILP Fleet Allocation Engine
===============================================

ROOT-CAUSE FIX (Bug #2):
    PuLP .varValue returns None (not 0.0) when the default solver is used
    without an explicit solver instance or when the variable is at its lower
    bound and the result was not explicitly written.  Calling int(None) raises
    TypeError which was being silently swallowed, producing all-zero allocations.

Changes made:
    1. Explicit PULP_CBC_CMD(msg=0) — deterministic solver, suppressed noise.
    2. _safe_var() helper — guards every .varValue access against None.
    3. Comprehensive diagnostic logging at every stage.
    4. Post-solve constraint verification logged per route.
    5. Objective value extracted and logged after solve.
"""

import logging
import math
from typing import Dict, Any, List

import pulp

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Safe variable value extractor
# ---------------------------------------------------------------------------
def _safe_var(lp_var: pulp.LpVariable, default: float = 0.0) -> float:
    """
    Safely extract a solved value from a PuLP decision variable.

    PuLP's .varValue returns None (not 0.0) in several edge cases:
      - Solver did not run (status INFEASIBLE before solve).
      - CBC is not on PATH and PuLP silently fell back without solving.
      - The variable was at its lower-bound but the solution vector was not
        written back (a known CBC/PuLP edge case on Windows).

    Returning ``default`` (0.0) here is intentional: if we cannot read the
    value, we conservatively assume zero buses were assigned, which is then
    surfaced via unmet_demand in the summary.
    """
    val = lp_var.varValue
    if val is None:
        logger.warning(
            "MILP_DIAG | varValue is None for variable '%s' — defaulting to %.1f",
            lp_var.name, default,
        )
        return default
    return float(val)


# ---------------------------------------------------------------------------
# Main optimization function
# ---------------------------------------------------------------------------
def optimize_fleet(
    route_demands: Dict[str, int],
    bus_capacity: int = 50,
    max_buses_per_route: int = 10,
    max_total_buses: int = 100,
    cost_per_bus: float = 1000.0,
    penalty_unmet_demand: float = 50.0,
    alpha: float = 1.0,
    beta: float = 0.7,
    gamma: float = 2.0,
    delta: float = 1.5,
) -> Dict[str, Any]:
    """
    MILP optimisation for bus fleet allocation.

    route_demands: Dict mapping route_id → total passenger demand.

    Objective (minimise):
        α * buses_assigned
        β * unused_capacity
        γ * unmet_demand          ← heavy penalty drives demand satisfaction
        δ * under_utilization

    Returns a dict with keys:
        status          : PuLP status string ("Optimal" | "Feasible" | "error")
        route_allocation: List[dict] per route
        summary         : aggregate KPIs
    """
    routes = list(route_demands.keys())
    n_routes = len(routes)
    total_demand_input = sum(route_demands.values())

    logger.info(
        "MILP_DIAG | ===== optimize_fleet START ===== | routes=%d | "
        "total_demand=%d | bus_capacity=%d | max_buses_per_route=%d",
        n_routes, total_demand_input, bus_capacity, max_buses_per_route,
    )
    logger.info(
        "MILP_DIAG | Objective weights: alpha=%.2f beta=%.2f gamma=%.2f delta=%.2f",
        alpha, beta, gamma, delta,
    )
    logger.info("MILP_DIAG | route_demands=%s", dict(list(route_demands.items())[:20]))

    if not routes:
        logger.warning("MILP_DIAG | No routes provided — returning empty result.")
        return {
            "status": "empty",
            "route_allocation": [],
            "summary": {
                "total_buses_used": 0,
                "total_passengers_demand": 0,
                "total_passengers_served": 0,
                "overall_efficiency_percent": 0.0,
                "total_unmet_demand": 0,
            },
        }

    # ── Build the problem ────────────────────────────────────────────────────
    prob = pulp.LpProblem("Bus_Fleet_Optimization", pulp.LpMinimize)

    # Decision variables
    buses_assigned = pulp.LpVariable.dicts(
        "Buses", routes, lowBound=0, upBound=max_buses_per_route, cat=pulp.LpInteger
    )
    served_passengers = pulp.LpVariable.dicts(
        "Served", routes, lowBound=0, cat=pulp.LpContinuous
    )
    unmet_demand = pulp.LpVariable.dicts(
        "Unmet", routes, lowBound=0, cat=pulp.LpContinuous
    )
    unused_capacity = pulp.LpVariable.dicts(
        "Unused", routes, lowBound=0, cat=pulp.LpContinuous
    )
    under_utilization = pulp.LpVariable.dicts(
        "UnderUtil", routes, lowBound=0, cat=pulp.LpContinuous
    )

    logger.info(
        "MILP_DIAG | Variables created: %d buses_assigned + %d served + "
        "%d unmet + %d unused + %d under_util",
        len(buses_assigned), len(served_passengers), len(unmet_demand),
        len(unused_capacity), len(under_utilization),
    )

    # Objective
    prob += pulp.lpSum([
        alpha * buses_assigned[r]
        + beta  * unused_capacity[r]
        + gamma * unmet_demand[r]
        + delta * under_utilization[r]
        for r in routes
    ])

    # Constraints
    n_constraints = 0
    for r in routes:
        d = route_demands[r]

        # 1. Demand balance: served + unmet = total demand
        prob += (
            served_passengers[r] + unmet_demand[r] == d,
            f"Demand_Balance_{r}",
        )
        # 2. Capacity: buses * capacity >= served
        prob += (
            buses_assigned[r] * bus_capacity >= served_passengers[r],
            f"Capacity_{r}",
        )
        # 3. Unused capacity definition
        prob += (
            unused_capacity[r] == buses_assigned[r] * bus_capacity - served_passengers[r],
            f"Unused_{r}",
        )
        # 4. Under-utilization penalty (linearised: util < 75%)
        prob += (
            under_utilization[r] >= 0.75 * buses_assigned[r] * bus_capacity - served_passengers[r],
            f"UnderUtil_{r}",
        )
        n_constraints += 4

        # 5. Minimum service guarantee: if any demand exists on a route,
        #    at least 1 bus MUST be assigned.  Without this, the solver may
        #    decide the bus cost outweighs the unmet-demand penalty for small
        #    demand values, producing the all-zero solution that is
        #    mathematically optimal but operationally invalid.
        if d > 0:
            prob += (
                buses_assigned[r] >= 1,
                f"MinService_{r}",
            )
            n_constraints += 1

    # 6. Global Fleet Size Constraint
    prob += (
        pulp.lpSum([buses_assigned[r] for r in routes]) <= max_total_buses,
        "Global_Fleet_Size",
    )
    n_constraints += 1

    logger.info("MILP_DIAG | Constraints added: %d total across %d routes",
                n_constraints, n_routes)

    # ── Solve ────────────────────────────────────────────────────────────────
    # Use CBC explicitly with suppressed output.  This avoids the silent
    # fallback path where PuLP pretends to solve but leaves .varValue = None.
    try:
        solver = pulp.PULP_CBC_CMD(msg=0)
        prob.solve(solver)
    except Exception as e:
        logger.exception("MILP_DIAG | Solver raised exception: %s", e)
        return {"status": "error", "error_details": str(e)}

    solver_status_int = prob.status
    solver_status_str = pulp.LpStatus.get(solver_status_int, "Unknown")
    objective_value = pulp.value(prob.objective)

    logger.info(
        "MILP_DIAG | ===== SOLVER RESULT ===== | status_int=%d | status_str=%s | "
        "objective_value=%s",
        solver_status_int, solver_status_str, objective_value,
    )

    if solver_status_str not in ("Optimal", "Feasible"):
        logger.error(
            "MILP_DIAG | Solver did not reach Optimal/Feasible — aborting. status=%s",
            solver_status_str,
        )
        return {
            "status": "error",
            "error_details": f"Solver returned status: {solver_status_str}",
        }

    # ── Extract results ──────────────────────────────────────────────────────
    allocation: List[Dict[str, Any]] = []
    total_buses = 0
    total_unmet  = 0
    total_capacity = 0
    total_demand = sum(route_demands.values())

    logger.info("MILP_DIAG | ===== PER-ROUTE VARIABLE VALUES =====")

    for r in routes:
        # --- safe extraction (Bug #2 fix) ---
        buses_val    = _safe_var(buses_assigned[r],    default=0.0)
        served_val   = _safe_var(served_passengers[r], default=0.0)
        unmet_val    = _safe_var(unmet_demand[r],      default=float(route_demands[r]))
        unused_val   = _safe_var(unused_capacity[r],   default=0.0)
        underutil_val= _safe_var(under_utilization[r], default=0.0)

        buses     = max(0, int(round(buses_val)))
        served    = max(0, int(round(served_val)))
        unmet     = max(0, int(round(unmet_val)))
        demanded  = route_demands[r]

        # Recalculate utilization from extracted values
        capacity_provided = buses * bus_capacity
        utilization = (
            round((served / capacity_provided) * 100, 2)
            if capacity_provided > 0 else 0.0
        )

        # Constraint satisfaction check
        demand_balance_ok = abs((served + unmet) - demanded) < 1.0
        capacity_ok = (buses * bus_capacity) >= (served - 0.5)

        logger.info(
            "MILP_DIAG | route=%s | demand=%d | buses_raw=%.4f → %d | "
            "served_raw=%.4f → %d | unmet_raw=%.4f → %d | "
            "unused=%.4f | underutil=%.4f | utilization=%.2f%% | "
            "demand_balance_ok=%s | capacity_ok=%s",
            r, demanded,
            buses_val, buses,
            served_val, served,
            unmet_val, unmet,
            unused_val, underutil_val,
            utilization, demand_balance_ok, capacity_ok,
        )

        total_buses    += buses
        total_unmet    += unmet
        total_capacity += capacity_provided

        allocation.append({
            "route_id":           r,
            "buses_assigned":     buses,
            "demand":             demanded,
            "unmet_demand":       unmet,
            "utilization_percent": utilization,
        })

    overall_efficiency = (
        round((total_demand - total_unmet) / total_capacity * 100, 2)
        if total_capacity > 0 else 0.0
    )

    logger.info(
        "MILP_DIAG | ===== FINAL SUMMARY ===== | total_buses=%d | "
        "total_demand=%d | total_served=%d | total_unmet=%d | "
        "overall_efficiency=%.2f%%",
        total_buses, total_demand, total_demand - total_unmet,
        total_unmet, overall_efficiency,
    )

    return {
        "status": solver_status_str,
        "route_allocation": allocation,
        "summary": {
            "total_buses_used":          total_buses,
            "total_passengers_demand":   total_demand,
            "total_passengers_served":   total_demand - total_unmet,
            "overall_efficiency_percent": overall_efficiency,
            "total_unmet_demand":        total_unmet,
        },
    }
