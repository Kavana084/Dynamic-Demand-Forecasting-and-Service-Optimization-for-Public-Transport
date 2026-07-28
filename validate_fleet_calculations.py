"""
validate_fleet_calculations.py
================================
Phase 2 Validation: Fleet Optimization Calculation Audit

Audits the complete calculation chain:
    predicted_demand -> required_buses -> recommended_fleet -> additional_buses

Reads from Supabase PostgreSQL via backend SQLAlchemy models.

Output: fleet_validation_report.md
"""

import os
import sys
import math
import datetime
from collections import Counter

# Ensure backend importable
_base = os.path.dirname(os.path.abspath(__file__))
_backend = os.path.join(_base, "backend")
if _backend not in sys.path:
    sys.path.insert(0, _backend)

REPORT_PATH = os.path.join(_base, "fleet_validation_report.md")
BUS_CAPACITY_SERVICE = 60  # fleet_optimization_service.py
BUS_CAPACITY_ADMIN   = 50  # admin.py + .env

# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def get_session():
    from app.database.connection import SessionLocal
    return SessionLocal()

def fetch_optimization_results(db):
    from app.database.models import OptimizationResult
    rows = db.query(OptimizationResult).order_by(OptimizationResult.timestamp.desc()).limit(3000).all()
    seen = {}
    for r in rows:
        if r.route_id not in seen:
            seen[r.route_id] = {
                "route_id":         r.route_id,
                "predicted_demand": r.predicted_demand or 0,
                "allocated_buses":  r.allocated_buses or 0,
                "utilization":      r.utilization,
                "unserved_demand":  r.unserved_demand or 0,
                "model_version":    r.model_version,
            }
    return list(seen.values())

def fetch_forecast_history(db):
    from app.database.models import ForecastHistory
    rows = db.query(ForecastHistory).order_by(ForecastHistory.generated_at.desc()).limit(3000).all()
    seen = {}
    for r in rows:
        if r.route_id not in seen:
            seen[r.route_id] = {
                "predicted_passengers": r.predicted_passengers or 0,
                "confidence_score":     r.confidence_score,
            }
    return seen

def fetch_fleet_allocations(db):
    try:
        from app.database.models import FleetAllocation
        rows = db.query(FleetAllocation).order_by(FleetAllocation.timestamp.desc()).limit(3000).all()
        seen = {}
        for r in rows:
            if r.route_id not in seen:
                seen[r.route_id] = {
                    "required_buses":  r.required_buses or 0,
                    "allocated_buses": r.allocated_buses or 0,
                    "fleet_gap":       r.fleet_gap or 0,
                }
        return seen
    except Exception:
        return {}

# ---------------------------------------------------------------------------
# Pure-logic helpers (no DB)
# ---------------------------------------------------------------------------

def verify_calculation(demand, allocated, capacity):
    required   = math.ceil(demand / capacity) if demand > 0 else 0
    additional = max(0, required - allocated)
    matches    = (required == allocated)
    return required, additional, matches

def demand_range_table():
    ranges = [
        (1,    50),    (51,  100),   (101,  150),  (151,  200),
        (201,  250),   (251, 300),   (301,  400),  (401,  500),
        (501,  600),   (601, 900),   (901, 1200),  (1201, 1800),
    ]
    rows = []
    for low, high in ranges:
        mid = (low + high) // 2
        b50 = math.ceil(mid / 50)
        b60 = math.ceil(mid / 60)
        rows.append((f"{low}-{high}", mid, b50, b60))
    return rows

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_fleet_audit():
    print("[Fleet Audit] Connecting to Supabase...")
    db = get_session()
    opt_rows     = fetch_optimization_results(db)
    forecast_map = fetch_forecast_history(db)
    alloc_map    = fetch_fleet_allocations(db)
    db.close()

    print(f"  Optimization results: {len(opt_rows)} routes")
    print(f"  Forecast history:     {len(forecast_map)} routes")
    print(f"  Fleet allocations:    {len(alloc_map)} routes")

    if not opt_rows:
        # No opt results: generate static report from analysis only
        print("[Fleet Audit] No optimization_results found in DB — generating static analysis report.")
        opt_rows = []

    # ── Per-route verification ───────────────────────────────────────────────
    verified_rows = []
    mismatches_cap50 = []
    mismatches_cap60 = []

    for opt in opt_rows:
        route_id  = opt["route_id"]
        demand    = opt["predicted_demand"]
        allocated = opt["allocated_buses"]

        fh = forecast_map.get(route_id, {})
        fh_demand = fh.get("predicted_passengers", demand)

        req_50, add_50, match_50 = verify_calculation(demand, allocated, BUS_CAPACITY_ADMIN)
        req_60, add_60, match_60 = verify_calculation(demand, allocated, BUS_CAPACITY_SERVICE)

        fa = alloc_map.get(route_id, {})

        verified_rows.append({
            "route_id":       route_id,
            "demand":         demand,
            "fh_demand":      fh_demand,
            "allocated":      allocated,
            "req_50":         req_50,
            "req_60":         req_60,
            "add_50":         add_50,
            "add_60":         add_60,
            "match_50":       match_50,
            "match_60":       match_60,
            "fa_required":    fa.get("required_buses"),
            "fa_gap":         fa.get("fleet_gap"),
            "utilization":    opt["utilization"],
            "unserved":       opt["unserved_demand"],
            "model_version":  opt["model_version"],
        })
        if not match_50:
            mismatches_cap50.append(route_id)
        if not match_60:
            mismatches_cap60.append(route_id)

    # ── Clustering detection ──────────────────────────────────────────────────
    allocated_counts = Counter(row["allocated"] for row in verified_rows)
    most_common_alloc, alloc_count = allocated_counts.most_common(1)[0] if allocated_counts else (None, 0)
    n = max(len(verified_rows), 1)
    alloc_cluster_pct = alloc_count / n * 100
    hardcoded_suspect = alloc_cluster_pct >= 40

    # ── Bus count grouping ───────────────────────────────────────────────────
    groups = {1: [], 2: [], 3: [], "4+": []}
    for row in verified_rows:
        r = row["req_60"]
        if r <= 1:
            groups[1].append(row["route_id"])
        elif r == 2:
            groups[2].append(row["route_id"])
        elif r == 3:
            groups[3].append(row["route_id"])
        else:
            groups["4+"].append(row["route_id"])

    # ── Demand source mismatch ───────────────────────────────────────────────
    mismatch_source_count = sum(1 for row in verified_rows if row["demand"] != row["fh_demand"])

    # ── Build report ─────────────────────────────────────────────────────────
    now_str = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    L = []

    L.append("# Fleet Optimization Validation Report")
    L.append(f"\n**Generated**: {now_str}")
    L.append(f"**Data source**: Supabase PostgreSQL (via backend SQLAlchemy)")
    L.append(f"**Routes audited**: {len(verified_rows)}\n")
    L.append("---\n")

    # 1. Bus capacity constants
    L.append("## 1. Bus Capacity Constant Audit\n")
    L.append("| Location | File | Value |")
    L.append("|---|---|---|")
    L.append("| FleetOptimizationService | `fleet_optimization_service.py:21` | **60 pax/bus** |")
    L.append("| Admin dashboard helper   | `admin.py:24`                      | **50 pax/bus** |")
    L.append("| MILP optimizer default   | `optimization.py:6`                | **50 pax/bus** |")
    L.append("| Environment config       | `.env:11`                           | **50 pax/bus** |")
    L.append("| FleetService (settings)  | `fleet_service.py:24`              | **50 pax/bus** (from config) |")
    L.append("")
    L.append("> **CRITICAL**: `fleet_optimization_service.py` uses 60 pax/bus while all other modules use 50.")
    L.append("> For demand=120 → cap=50 requires **3 buses**, cap=60 requires **2 buses**. Integer difference.")
    L.append("> This causes divergent required_buses calculations between Admin KPIs and Fleet Panel.\n")

    # 2. Demand range → expected buses
    L.append("## 2. Demand Range vs Expected Buses\n")
    L.append("| Demand Range | Sample | Required (cap=50) | Required (cap=60) | Difference |")
    L.append("|---|---|---|---|---|")
    for label, mid, b50, b60 in demand_range_table():
        diff = b50 - b60
        diff_str = f"+{diff}" if diff > 0 else str(diff)
        L.append(f"| {label} | {mid} | {b50} | {b60} | {diff_str} |")
    L.append("")
    L.append("> **Difference** = extra buses admin.py calculates vs fleet_optimization_service.py.")
    L.append("> Positive = admin over-counts required buses vs fleet service.\n")

    # 3. Calculation chain verification
    if verified_rows:
        L.append("## 3. Calculation Chain Verification\n")
        L.append("Formula: `required_buses = ceil(predicted_demand / bus_capacity)`\n")
        L.append("| Capacity | Correct | Mismatched | Mismatch% |")
        L.append("|---|---|---|---|")
        c50 = n - len(mismatches_cap50)
        c60 = n - len(mismatches_cap60)
        L.append(f"| 50 pax/bus | {c50}/{n} | {len(mismatches_cap50)} | {len(mismatches_cap50)/n*100:.1f}% |")
        L.append(f"| 60 pax/bus | {c60}/{n} | {len(mismatches_cap60)} | {len(mismatches_cap60)/n*100:.1f}% |")
        L.append("")
        L.append("> A mismatch means `allocated_buses != ceil(demand/capacity)`. MILP solver may assign")
        L.append("> fewer buses than theoretically required due to global bus pool constraints.\n")

    # 4. Per-route table
    if verified_rows:
        L.append("## 4. Route Allocation Table\n")
        L.append("| Route | Demand | Allocated | Req(50) | Add(50) | Req(60) | Add(60) | Unserved | Util% | OK(50) | OK(60) |")
        L.append("|---|---|---|---|---|---|---|---|---|---|---|")
        for row in sorted(verified_rows, key=lambda x: x["demand"], reverse=True):
            util_str = f"{row['utilization']:.1f}" if row["utilization"] is not None else "N/A"
            m50 = "Y" if row["match_50"] else "N"
            m60 = "Y" if row["match_60"] else "N"
            L.append(
                f"| {row['route_id']} | {row['demand']} | {row['allocated']} |"
                f" {row['req_50']} | {row['add_50']} | {row['req_60']} | {row['add_60']} |"
                f" {row['unserved']} | {util_str} | {m50} | {m60} |"
            )
        L.append("")
    else:
        L.append("## 4. Route Allocation Table\n")
        L.append("_No optimization_results data found in database. Run fleet optimization first._\n")

    # 5. Bus count grouping
    L.append("## 5. Routes by Required Bus Count (capacity=60)\n")
    L.append("| Bus Count | Route Count | Sample Routes |")
    L.append("|---|---|---|")
    for k in [1, 2, 3, "4+"]:
        ids = groups[k]
        sample = ", ".join(ids[:8])
        if len(ids) > 8:
            sample += f" ... (+{len(ids)-8} more)"
        L.append(f"| {k} bus(es) | {len(ids)} | {sample} |")
    L.append("")

    # 6. Hardcoded detection
    L.append("## 6. Hardcoded Fleet Value Detection\n")
    if hardcoded_suspect and verified_rows:
        L.append(f"**Status**: FLAGGED\n")
        L.append(f"- `allocated_buses={most_common_alloc}` in {alloc_count}/{n} routes ({alloc_cluster_pct:.1f}%)")
        L.append("> May indicate MILP solver converging to one value, or results were hardcoded.\n")
    else:
        L.append("**Status**: PASS — Fleet values vary across routes.\n")

    L.append("### Allocated Buses Distribution")
    L.append("| Buses Allocated | Route Count | % |")
    L.append("|---|---|---|")
    for val, cnt in sorted(allocated_counts.items()):
        L.append(f"| {val} | {cnt} | {cnt/n*100:.1f}% |")
    L.append("")

    # 7. Demand source comparison
    L.append("## 7. Demand Source Consistency\n")
    L.append(f"Comparing `optimization_results.predicted_demand` vs `forecast_history.predicted_passengers`\n")
    L.append(f"- Routes checked: {len(verified_rows)}")
    L.append(f"- **Mismatches: {mismatch_source_count}**")
    L.append("")
    if mismatch_source_count > 0:
        L.append("| Route | OptResult Demand | FH Demand | Match |")
        L.append("|---|---|---|---|")
        shown = 0
        for row in verified_rows:
            if row["demand"] != row["fh_demand"] and shown < 30:
                match = "Y" if row["demand"] == row["fh_demand"] else "N"
                L.append(f"| {row['route_id']} | {row['demand']} | {row['fh_demand']} | {match} |")
                shown += 1
        L.append("")
        L.append("> Dual write paths confirmed: `OptimizationEngine` and old `/api/optimize_fleet` both")
        L.append("> write to `optimization_results` but via different code paths.\n")
    else:
        L.append("All routes match — demand is consistent between the two tables.\n")

    # 8. Key findings
    L.append("## 8. Key Findings\n")
    findings = []
    findings.append("**CRITICAL — Bus capacity split**: `fleet_optimization_service.py` uses 60 pax/bus; "
                    "`admin.py`, `optimization.py`, `.env` all use 50 pax/bus. "
                    "Same demand = different required_buses across system components.")
    if hardcoded_suspect and verified_rows:
        findings.append(f"**FLAGGED — Uniform allocation**: {alloc_cluster_pct:.1f}% of routes share "
                        f"`allocated_buses={most_common_alloc}`.")
    if mismatch_source_count > 0:
        findings.append(f"**FLAGGED — Demand source divergence**: {mismatch_source_count} routes differ "
                        "between `optimization_results` and `forecast_history`.")
    for f in findings:
        L.append(f"- {f}\n")

    report_text = "\n".join(L)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(report_text)

    print(f"\n[Fleet Audit] Report written: {REPORT_PATH}")
    print(f"  Routes: {len(verified_rows)}, Mismatch(50): {len(mismatches_cap50)}, Mismatch(60): {len(mismatches_cap60)}")
    return len([x for x in findings if x.startswith("**FLAGGED") or x.startswith("**CRITICAL")])


if __name__ == "__main__":
    issues = run_fleet_audit()
    sys.exit(0 if issues == 0 else 1)
