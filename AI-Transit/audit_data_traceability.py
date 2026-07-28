"""
audit_data_traceability.py
==========================
Phase 2 Validation: Cross-System Data Consistency

Compares values shown in:
  - Passenger Portal (/api/predict_demand)
  - Fleet Optimization Panel (/api/fleet/optimize -> OptimizationEngine)
  - Admin Dashboard (/api/admin/overview-kpis, /api/admin/optimization/insights)

Output: system_data_traceability_matrix.md
"""

import os
import sys
import math
import datetime

_base = os.path.dirname(os.path.abspath(__file__))
_backend = os.path.join(_base, "backend")
if _backend not in sys.path:
    sys.path.insert(0, _backend)

REPORT_PATH = os.path.join(_base, "system_data_traceability_matrix.md")

# ---------------------------------------------------------------------------
# Static field-level traceability map
# ---------------------------------------------------------------------------

DATA_SOURCES = {
    "predicted_demand": {
        "Passenger Portal":            "/api/predict_demand -> PredictionService.predict_demand() -> CatBoost LIVE (hardcoded defaults for 55/57 features including day_of_week='Monday', month=1, temperature=28)",
        "Fleet Optimization Panel":    "/api/fleet/optimize -> OptimizationEngine.run() -> reads ForecastHistory DB (latest per route) -> MILP solver",
        "Admin Dashboard KPIs":        "/api/admin/overview-kpis -> ForecastHistory.predicted_passengers (SUM, latest per route)",
        "Admin Optimization Insights": "/api/admin/optimization/insights -> OptimizationResult.predicted_demand",
    },
    "occupancy_percent": {
        "Passenger Portal":            "NOT RETURNED — /api/predict_demand does not include occupancy_percent",
        "Fleet Optimization Panel":    "NOT SHOWN — response contains utilization_percent (derived) not raw occupancy",
        "Admin Dashboard KPIs":        "/api/admin/tables/recent-demand -> DemandHistory.occupancy_percent (direct DB read)",
        "Admin Optimization Insights": "NOT INCLUDED",
    },
    "required_buses": {
        "Passenger Portal":            "NOT DISPLAYED",
        "Fleet Optimization Panel":    "MILP solver output: buses_assigned (capacity=60 via fleet_optimization_service)",
        "Admin Dashboard KPIs":        "admin.py:287 _required_buses() = ceil(demand/50) — hardcoded 50 pax/bus",
        "Admin Optimization Insights": "admin.py:507 _required_buses() = ceil(demand/50) — hardcoded 50 pax/bus",
    },
    "current_fleet": {
        "Passenger Portal":            "NOT DISPLAYED",
        "Fleet Optimization Panel":    "available_buses is an INPUT param (not from DB); no current fleet read",
        "Admin Dashboard KPIs":        "OptimizationResult.allocated_buses (SUM, latest per route)",
        "Admin Optimization Insights": "OptimizationResult.allocated_buses",
    },
    "recommendation": {
        "Passenger Portal":            "FleetOptimizationService.generate_passenger_recommendation() — text based on ETA/occupancy/traffic/weather",
        "Fleet Optimization Panel":    "OptimizationEngine: dynamic text — 'Increase frequency - N unserved' or 'Decrease frequency - low utilization' or 'Maintain current frequency'",
        "Admin Dashboard Insights":    "get_dashboard_insights() — % change in ForecastHistory + capacity risk + pipeline failures",
        "Admin Optimization Insights": "fleet_optimization_service.generate_recommendation() — fleet_gap + utilization text",
    },
    "confidence": {
        "Passenger Portal":            "HARDCODED 85% — PredictDemand.jsx:42 sets `confidence: 85` as frontend fallback; CatBoost confidence_score NOT forwarded by /api/predict_demand",
        "Fleet Optimization Panel":    "NOT DISPLAYED",
        "Admin Dashboard KPIs":        "ForecastHistory.confidence_score (AVG) — real CatBoost model output",
        "Admin Optimization Insights": "ForecastHistory.confidence_score (AVG per route) — real model output",
    },
    "bus_capacity": {
        "Passenger Portal":            "N/A",
        "Fleet Optimization Panel":    "60 pax/bus (fleet_optimization_service.py:21 DEFAULT_BUS_CAPACITY=60)",
        "Admin Dashboard KPIs":        "50 pax/bus (admin.py:24 DEFAULT_BUS_CAPACITY=50)",
        "Admin Optimization Insights": "50 pax/bus (admin.py:287 _required_buses uses DEFAULT_BUS_CAPACITY=50)",
    },
}

CONSISTENCY_FLAGS = {
    "predicted_demand": {
        "consistent": False,
        "reason": "Passenger Portal calls ML live with hardcoded feature defaults. Fleet Panel and Admin both read ForecastHistory DB. Live prediction may differ from stored forecast if route-specific features diverge.",
    },
    "occupancy_percent": {
        "consistent": False,
        "reason": "Only Admin shows occupancy_percent (from DemandHistory). No cross-page comparison possible. Passenger Portal and Fleet Panel do not surface this field at all.",
    },
    "required_buses": {
        "consistent": False,
        "reason": "Admin uses capacity=50, Fleet Panel MILP uses capacity=60. Same demand value produces different required_buses in different parts of the system.",
    },
    "current_fleet": {
        "consistent": True,
        "reason": "Both Admin panels read from OptimizationResult.allocated_buses. Consistent source, though Fleet Panel does not show this field.",
    },
    "recommendation": {
        "consistent": False,
        "reason": "Four separate recommendation generators with different inputs, logic, and text. No shared recommendation service exists.",
    },
    "confidence": {
        "consistent": False,
        "reason": "Passenger Portal shows hardcoded 85%. Admin shows real DB confidence (~0.97). These are different values representing different things.",
    },
    "bus_capacity": {
        "consistent": False,
        "reason": "Fleet Panel path uses 60 pax/bus; Admin path uses 50 pax/bus. The same physical bus fleet is modeled with two different capacity constants.",
    },
}

# ---------------------------------------------------------------------------
# DB cross-validation using SQLAlchemy
# ---------------------------------------------------------------------------

def check_db_consistency():
    try:
        from app.database.connection import SessionLocal
        from app.database.models import OptimizationResult, ForecastHistory, DemandHistory
        from sqlalchemy import func

        db = SessionLocal()

        # Latest optimization per route
        opt_rows = db.query(OptimizationResult).order_by(OptimizationResult.timestamp.desc()).limit(3000).all()
        opt_map = {}
        for r in opt_rows:
            if r.route_id not in opt_map:
                opt_map[r.route_id] = {"demand": r.predicted_demand or 0, "allocated": r.allocated_buses or 0, "model": r.model_version}

        # Latest forecast per route
        fh_rows = db.query(ForecastHistory).order_by(ForecastHistory.generated_at.desc()).limit(3000).all()
        fh_map = {}
        for r in fh_rows:
            if r.route_id not in fh_map:
                fh_map[r.route_id] = {"demand": r.predicted_passengers or 0, "confidence": r.confidence_score}

        # Avg occupancy/pax per route
        dh_rows = db.query(
            DemandHistory.route_id,
            func.avg(DemandHistory.occupancy_percent).label("occ"),
            func.avg(DemandHistory.passenger_count).label("pax"),
        ).group_by(DemandHistory.route_id).all()
        dh_map = {r.route_id: {"occ": r.occ, "pax": r.pax} for r in dh_rows}

        db.close()

        all_routes = set(opt_map.keys()) | set(fh_map.keys())
        results = []
        for route_id in sorted(all_routes):
            opt = opt_map.get(route_id, {})
            fh  = fh_map.get(route_id, {})
            dh  = dh_map.get(route_id, {})
            opt_d = opt.get("demand")
            fh_d  = fh.get("demand")
            demand_match = (opt_d == fh_d) if (opt_d is not None and fh_d is not None) else None
            req_50 = math.ceil(opt_d / 50) if opt_d else None
            req_60 = math.ceil(opt_d / 60) if opt_d else None
            results.append({
                "route_id":     route_id,
                "opt_demand":   opt_d,
                "fh_demand":    fh_d,
                "demand_match": demand_match,
                "allocated":    opt.get("allocated"),
                "req_50":       req_50,
                "req_60":       req_60,
                "confidence":   fh.get("confidence"),
                "occ_avg":      dh.get("occ"),
                "pax_avg":      dh.get("pax"),
                "opt_model":    opt.get("model"),
            })
        return results, True
    except Exception as e:
        print(f"  [DB] Cross-check failed: {e}")
        return [], False

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_traceability_audit():
    print("[Traceability] Running cross-system consistency check...")
    db_results, db_available = check_db_consistency()
    print(f"  DB available: {db_available}, Routes: {len(db_results)}")

    now_str = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    L = []

    L.append("# System Data Traceability Matrix")
    L.append(f"\n**Generated**: {now_str}")
    L.append(f"**DB available**: {db_available}")
    L.append(f"**Scope**: Cross-page field-level data origin analysis\n")
    L.append("---\n")

    # 1. Per-field traceability
    L.append("## 1. Field-Level Traceability Matrix\n")
    pages = [
        "Passenger Portal",
        "Fleet Optimization Panel",
        "Admin Dashboard KPIs",
        "Admin Optimization Insights",
    ]
    for field, sources in DATA_SOURCES.items():
        flag = CONSISTENCY_FLAGS.get(field, {})
        consistent = flag.get("consistent", True)
        icon = "CONSISTENT" if consistent else "INCONSISTENT"
        L.append(f"### `{field}` — {'OK' if consistent else 'INCONSISTENT'}\n")
        if not consistent:
            L.append(f"> **Issue**: {flag.get('reason', '')}\n")
        L.append("| Page / Component | Data Source |")
        L.append("|---|---|")
        for page in pages:
            src = sources.get(page, "—")
            L.append(f"| {page} | {src} |")
        L.append("")

    # 2. Summary matrix
    L.append("## 2. Consistency Summary\n")
    L.append("| Field | Consistent? | Root Cause |")
    L.append("|---|---|---|")
    for field, flag in CONSISTENCY_FLAGS.items():
        c = "YES" if flag["consistent"] else "NO"
        reason_short = flag["reason"][:120] + ("..." if len(flag["reason"]) > 120 else "")
        L.append(f"| `{field}` | {c} | {reason_short} |")
    L.append("")

    inconsistent_count = sum(1 for f in CONSISTENCY_FLAGS.values() if not f["consistent"])
    L.append(f"**Inconsistent fields: {inconsistent_count}/{len(CONSISTENCY_FLAGS)}**\n")

    # 3. DB cross-validation
    L.append("## 3. Database Cross-Validation (optimization_results vs forecast_history)\n")
    if db_results:
        mismatches = [r for r in db_results if r["demand_match"] is False]
        matches    = [r for r in db_results if r["demand_match"] is True]
        unknowns   = [r for r in db_results if r["demand_match"] is None]

        L.append("| Category | Count |")
        L.append("|---|---|")
        L.append(f"| Matching demand | {len(matches)} |")
        L.append(f"| **MISMATCHED demand** | **{len(mismatches)}** |")
        L.append(f"| In one table only | {len(unknowns)} |")
        L.append(f"| Total routes | {len(db_results)} |")
        L.append("")

        if mismatches:
            L.append("### Mismatch Detail\n")
            L.append("| Route | OptResult Demand | FH Demand | Req(50) | Req(60) | Allocated | Confidence |")
            L.append("|---|---|---|---|---|---|---|")
            for r in mismatches[:30]:
                conf = f"{r['confidence']:.3f}" if r["confidence"] else "N/A"
                L.append(f"| {r['route_id']} | {r['opt_demand']} | {r['fh_demand']} | {r['req_50']} | {r['req_60']} | {r['allocated']} | {conf} |")
            L.append("")

        L.append("### Full Table (first 50 routes)\n")
        L.append("| Route | Opt Demand | FH Demand | Match | Req(50) | Req(60) | Allocated | Occ% | Pax Avg | Confidence |")
        L.append("|---|---|---|---|---|---|---|---|---|---|")
        for r in db_results[:50]:
            match_icon = "Y" if r["demand_match"] else ("N" if r["demand_match"] is False else "-")
            occ  = f"{r['occ_avg']:.1f}" if r["occ_avg"] else "N/A"
            pax  = f"{r['pax_avg']:.1f}" if r["pax_avg"] else "N/A"
            conf = f"{r['confidence']:.3f}" if r["confidence"] else "N/A"
            r50  = r["req_50"] if r["req_50"] else "N/A"
            r60  = r["req_60"] if r["req_60"] else "N/A"
            L.append(
                f"| {r['route_id']} | {r['opt_demand'] or 'N/A'} | {r['fh_demand'] or 'N/A'} | {match_icon} |"
                f" {r50} | {r60} | {r['allocated'] or 'N/A'} | {occ} | {pax} | {conf} |"
            )
        L.append("")
    else:
        L.append("_No database data available._\n")

    # 4. Recommended single source of truth
    L.append("## 4. Recommended Single Source of Truth\n")
    L.append("| Field | Recommended Source | Rationale |")
    L.append("|---|---|---|")
    L.append("| `predicted_demand` | `ForecastHistory.predicted_passengers` (latest per route) | Written by CatBoost pipeline; consistent between Admin and Fleet. Passenger Portal should read this instead of calling ML live. |")
    L.append("| `required_buses`   | `ceil(demand / 60)` — fleet_optimization_service standard | 60 pax/bus = operational vehicle capacity. Admin.py should be updated to 60. |")
    L.append("| `current_fleet`    | `OptimizationResult.allocated_buses` (latest per route) | Only reliable persistent allocation record. |")
    L.append("| `occupancy_percent`| `DemandHistory.occupancy_percent` | Only table storing observed occupancy. |")
    L.append("| `confidence`       | `ForecastHistory.confidence_score` | Real model output (~0.97). Replaces hardcoded 85% in frontend. |")
    L.append("| `bus_capacity`     | 60 pax/bus (standardize all constants) | Remove DEFAULT_BUS_CAPACITY=50 from admin.py; align all modules to 60. |")
    L.append("")

    # 5. Key findings
    L.append("## 5. Key Findings\n")
    L.append(f"- **{inconsistent_count} of {len(CONSISTENCY_FLAGS)} fields are INCONSISTENT** across system components.")
    L.append("- **Dual demand prediction pipelines**: Passenger Portal calls ML live; Fleet/Admin read ForecastHistory DB. Values may diverge.")
    L.append("- **Bus capacity split (50 vs 60)**: Admin and Fleet Panel compute different `required_buses` for the same demand.")
    L.append("- **Confidence hardcoded**: Passenger Portal shows 85% always. Admin shows real ~0.97 from model.")
    L.append("- **Recommendation fragmentation**: 4 separate generators — no shared service, no common format.")
    L.append("- **occupancy_percent invisible**: Only shown in Admin Recent Demand table. Not surfaced elsewhere.")
    if db_results:
        mismatches = sum(1 for r in db_results if r["demand_match"] is False)
        L.append(f"- **DB demand divergence**: {mismatches} routes have different demand in `optimization_results` vs `forecast_history`.")
    L.append("- **current_fleet is consistent**: Both Admin panels use OptimizationResult.allocated_buses correctly.")

    report_text = "\n".join(L)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(report_text)

    print(f"\n[Traceability] Report written: {REPORT_PATH}")
    print(f"  Inconsistent fields: {inconsistent_count}/{len(CONSISTENCY_FLAGS)}")
    return inconsistent_count


if __name__ == "__main__":
    issues = run_traceability_audit()
    sys.exit(0 if issues == 0 else 1)
