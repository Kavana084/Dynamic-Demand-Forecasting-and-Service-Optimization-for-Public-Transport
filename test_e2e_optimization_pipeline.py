"""
test_e2e_optimization_pipeline.py
===================================
End-to-end validation tests for the backend optimization pipeline.

Verifies:
  1. CatBoost model loads successfully via ModelLoader.
  2. Feature names are populated (from binary if model_config.json absent).
  3. PredictionService.model property reflects actual load state.
  4. demand_prediction_service.predict_legacy() returns non-zero demand.
  5. optimize_fleet() returns non-zero buses_assigned for non-zero demand.
  6. varValue extraction is safe (no None → TypeError).
  7. Full pipeline: demand → MILP → allocation dict correctly populated.

Run from project root:
    python test_e2e_optimization_pipeline.py
"""

import sys
import os
import io

# Force UTF-8 output on Windows to avoid cp1252 encoding errors
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Ensure backend package is importable
BACKEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

# NOTE: intentionally NOT calling os.chdir() — model_loader resolves paths
# against ROOT_DIR from config.py, so correct behavior is cwd-independent.

# ── Colour helpers ────────────────────────────────────────────────────────────
GREEN  = ""
RED    = ""
YELLOW = ""
RESET  = ""
BOLD   = ""

passed = []
failed = []
warnings = []


def ok(msg: str):
    print(f"  [PASS] {msg}")
    passed.append(msg)


def fail(msg: str, detail: str = ""):
    print(f"  [FAIL] {msg}")
    if detail:
        print(f"         {detail}")
    failed.append(msg)


def warn(msg: str):
    print(f"  [WARN] {msg}")
    warnings.append(msg)


def section(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


# =============================================================================
# Section 1: Model Loader
# =============================================================================
section("1. CatBoost ModelLoader")

try:
    from app.ml.model_loader import model_loader
    ok("ModelLoader imported successfully")
except Exception as e:
    fail("Failed to import ModelLoader", str(e))
    sys.exit(1)

try:
    load_result = model_loader.load_model()
    if load_result:
        ok(f"model_loader.load_model() → True")
    else:
        fail("model_loader.load_model() returned False — model did not load")
except Exception as e:
    fail("model_loader.load_model() raised an exception", str(e))

is_loaded = model_loader.is_model_loaded()
if is_loaded:
    ok(f"model_loader.is_model_loaded() → True")
else:
    fail("model_loader.is_model_loaded() → False")

feature_names = model_loader.get_feature_names()
if feature_names:
    ok(f"Feature names populated: {len(feature_names)} features")
    print(f"      First 5: {feature_names[:5]}")
else:
    fail(
        "Feature names list is EMPTY — Bug #3 may not be fixed",
        "Expected features from model binary (model.feature_names_) or model_config.json"
    )

cat_features = model_loader.get_categorical_features()
if cat_features:
    ok(f"Categorical features: {len(cat_features)}")
else:
    warn("Categorical features list is empty — may use fallback in predictor")


# =============================================================================
# Section 2: PredictionService model property (Bug #1 fix verification)
# =============================================================================
section("2. PredictionService.model property (Bug #1)")

try:
    from app.service import prediction_service, init_service
    ok("PredictionService imported")
except Exception as e:
    fail("Failed to import PredictionService", str(e))
    prediction_service = None

if prediction_service is not None:
    init_service()  # ensure init was called
    model_val = prediction_service.model
    if model_val is not None:
        ok(f"prediction_service.model → {type(model_val).__name__} (not None)")
    else:
        fail(
            "prediction_service.model is None — Bug #1 NOT fixed",
            "PredictionService.model property must delegate to model_loader.get_model()"
        )


# =============================================================================
# Section 3: Demand Prediction (end-to-end through CatBoost)
# =============================================================================
section("3. Demand Prediction via CatBoost")

try:
    from app.services.demand_prediction_service import demand_prediction_service
    ok("DemandPredictionService imported")
except Exception as e:
    fail("Failed to import DemandPredictionService", str(e))
    demand_prediction_service = None

if demand_prediction_service is not None:
    try:
        result = demand_prediction_service.predict_legacy(
            route_id="500",
            passenger_count=80,
            occupancy_percent=70.0,
            weather="Clear",
            traffic="Medium",
            hour_of_day=9,
        )
        route_pax = result.get("route_predicted_passengers", 0)
        model_src = result.get("model_source", "unknown")

        if route_pax > 0:
            ok(f"predict_legacy() → route_predicted_passengers={route_pax} | source={model_src}")
        else:
            fail(
                f"predict_legacy() returned 0 passengers (source={model_src})",
                "Expected non-zero demand from CatBoost or heuristic fallback"
            )

        if model_src == "catboost":
            ok("Model source confirmed: catboost (primary path active)")
        elif model_src == "heuristic":
            warn("Model source is 'heuristic' — CatBoost path failed, using fallback")
        else:
            warn(f"Unexpected model_source: {model_src}")

    except Exception as e:
        fail("predict_legacy() raised an exception", str(e))


# =============================================================================
# Section 4: MILP optimize_fleet() — variable extraction (Bug #2 fix)
# =============================================================================
section("4. MILP optimize_fleet() — varValue extraction (Bug #2)")

try:
    from app.optimization import optimize_fleet, _safe_var
    ok("optimize_fleet and _safe_var imported")
except Exception as e:
    fail("Failed to import optimization module", str(e))
    optimize_fleet = None

if optimize_fleet is not None:
    # Test _safe_var directly
    try:
        import pulp
        var_test = pulp.LpVariable("test_var", lowBound=0, cat=pulp.LpInteger)
        # Before solving, varValue is None — _safe_var must return default
        safe_result = _safe_var(var_test, default=0.0)
        if safe_result == 0.0:
            ok("_safe_var(None varValue, default=0.0) → 0.0 correctly")
        else:
            fail(f"_safe_var returned {safe_result} instead of 0.0")
    except Exception as e:
        fail("_safe_var test raised exception", str(e))

    # Test with known demands
    test_demands = {
        "ROUTE_A": 120,
        "ROUTE_B": 60,
        "ROUTE_C": 0,   # zero demand — trivial all-zero is valid
        "ROUTE_D": 180,
    }

    try:
        milp_result = optimize_fleet(
            route_demands=test_demands,
            bus_capacity=60,
            max_buses_per_route=10,
            alpha=1.0, beta=0.7, gamma=2.0, delta=1.5,
        )
        status = milp_result.get("status")
        alloc  = milp_result.get("route_allocation", [])
        summ   = milp_result.get("summary", {})

        print(f"\n    Solver status    : {status}")
        print(f"    Total buses used : {summ.get('total_buses_used')}")
        print(f"    Total demand     : {summ.get('total_passengers_demand')}")
        print(f"    Passengers served: {summ.get('total_passengers_served')}")
        print(f"    Unmet demand     : {summ.get('total_unmet_demand')}")
        print(f"    Efficiency       : {summ.get('overall_efficiency_percent')}%")
        print()

        if status in ("Optimal", "Feasible"):
            ok(f"Solver status: {status}")
        else:
            fail(f"Solver returned non-optimal status: {status}")

        # Verify per-route results
        alloc_by_route = {a["route_id"]: a for a in alloc}
        all_buses_ok = True
        for route_id, demand in test_demands.items():
            entry = alloc_by_route.get(route_id)
            if entry is None:
                fail(f"Route {route_id} missing from allocation output")
                all_buses_ok = False
                continue

            buses = entry["buses_assigned"]
            unmet = entry["unmet_demand"]
            util  = entry["utilization_percent"]

            if demand > 0:
                expected_min_buses = 1
                if buses >= expected_min_buses:
                    ok(f"Route {route_id}: demand={demand} → buses={buses}, unmet={unmet}, util={util}%")
                else:
                    fail(
                        f"Route {route_id}: demand={demand} but buses_assigned={buses} (should be ≥1)",
                        "Bug #2 not fixed — varValue extraction still returning zero"
                    )
                    all_buses_ok = False
            else:
                # Zero demand — buses=0 is correct
                if buses == 0:
                    ok(f"Route {route_id}: demand=0 → buses=0 (trivially optimal — correct)")
                else:
                    warn(f"Route {route_id}: demand=0 but buses={buses} (non-zero, suboptimal)")

        if all_buses_ok:
            ok("All non-zero demand routes have buses_assigned ≥ 1")

    except Exception as e:
        fail("optimize_fleet() raised an exception", str(e))
        import traceback
        traceback.print_exc()


# =============================================================================
# Section 5: Full pipeline trace (demand → MILP → allocation dict)
# =============================================================================
section("5. Full pipeline: predict → optimize (without DB)")

if demand_prediction_service is not None and optimize_fleet is not None:
    pipeline_routes = ["300", "500", "401", "201"]
    pipeline_demands = {}

    print("  Generating demands via predict_legacy():")
    for rid in pipeline_routes:
        try:
            r = demand_prediction_service.predict_legacy(
                route_id=rid,
                passenger_count=60,
                occupancy_percent=65.0,
                weather="Clear",
                traffic="Medium",
                hour_of_day=9,
            )
            d = r.get("route_predicted_passengers", 0)
            pipeline_demands[rid] = d
            src = r.get("model_source", "?")
            print(f"    route={rid} → demand={d} source={src}")
        except Exception as e:
            fail(f"predict_legacy failed for route {rid}", str(e))
            pipeline_demands[rid] = 50  # safe fallback for pipeline test

    if any(v > 0 for v in pipeline_demands.values()):
        ok(f"At least one route has non-zero demand: {pipeline_demands}")
    else:
        fail("All pipeline demands are zero — prediction pipeline broken")

    try:
        pipeline_result = optimize_fleet(
            route_demands=pipeline_demands,
            bus_capacity=60,
            max_buses_per_route=10,
        )
        p_status = pipeline_result.get("status")
        p_alloc  = pipeline_result.get("route_allocation", [])
        p_summ   = pipeline_result.get("summary", {})

        print(f"\n  Pipeline MILP result: status={p_status}")
        for a in p_alloc:
            print(f"    route={a['route_id']} demand={a['demand']} "
                  f"buses={a['buses_assigned']} unmet={a['unmet_demand']} "
                  f"util={a['utilization_percent']}%")

        # Verify no value is silently overwritten with zero
        non_zero_routes = [r for r, d in pipeline_demands.items() if d > 0]
        alloc_map = {a["route_id"]: a for a in p_alloc}
        for rid in non_zero_routes:
            a = alloc_map.get(rid, {})
            buses = a.get("buses_assigned", 0)
            if buses > 0:
                ok(f"Route {rid}: demand={pipeline_demands[rid]} → buses_assigned={buses} (non-zero ✓)")
            else:
                fail(
                    f"Route {rid}: demand={pipeline_demands[rid]} → buses_assigned=0 (ZERO — pipeline broken)",
                    "Values are being overwritten or MILP is returning zero despite non-zero demand"
                )

        total_buses = p_summ.get("total_buses_used", 0)
        if total_buses > 0:
            ok(f"summary.total_buses_used={total_buses} (non-zero)")
        else:
            fail("summary.total_buses_used=0 despite non-zero demands")

    except Exception as e:
        fail("Full pipeline optimize_fleet() raised exception", str(e))
        import traceback
        traceback.print_exc()


# =============================================================================
# Summary
# =============================================================================
section("VALIDATION SUMMARY")
print(f"  {GREEN}Passed : {len(passed)}{RESET}")
print(f"  {YELLOW}Warnings: {len(warnings)}{RESET}")
print(f"  {RED}Failed : {len(failed)}{RESET}")

if failed:
    print(f"\n  {RED}{BOLD}FAILED TESTS:{RESET}")
    for f in failed:
        print(f"    {RED}✗ {f}{RESET}")
    sys.exit(1)
else:
    print(f"\n  {GREEN}{BOLD}ALL TESTS PASSED{RESET}")
    sys.exit(0)
